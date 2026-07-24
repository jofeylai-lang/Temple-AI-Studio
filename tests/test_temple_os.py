from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.request
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.temple_os import TempleOSKernel


class TempleOSKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kernel = TempleOSKernel(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_initializes_platform_state(self) -> None:
        payload = self.kernel.ensure_initialized()
        self.assertIn("config", payload)
        self.assertTrue(self.kernel.paths.config.exists())
        self.assertTrue((self.kernel.paths.workspaces / "default" / "workspace.json").exists())
        status = self.kernel.status()
        self.assertEqual(status["version"], "0.1.0")
        self.assertGreaterEqual(status["providers"]["enabled"], 3)

    def test_provider_selection_is_local_first_and_paid_locked(self) -> None:
        image = self.kernel.providers.select("image", {"requiresEmma": True})
        self.assertFalse(image["requiresCEOApproval"])
        self.assertIn(image["selected"]["id"], {"comfyui-local", "local-template"})

        voice = self.kernel.providers.select("voice")
        self.assertTrue(voice["requiresCEOApproval"])
        self.assertIsNone(voice["selected"])

    def test_queue_worker_and_workflow(self) -> None:
        task = self.kernel.queue.enqueue("health-check", {}, priority=90)
        result = self.kernel.worker.run_once()
        self.assertTrue(result["processed"])
        self.assertEqual(result["task"]["id"], task["id"])
        self.assertEqual(result["task"]["status"], "completed")

        run = self.kernel.workflows.run("temple.health-check")
        self.assertEqual(len(run["taskIds"]), 1)
        second = self.kernel.worker.run_once()
        self.assertEqual(second["task"]["status"], "completed")

    def test_business_rules_block_destructive_and_paid_tasks(self) -> None:
        task = self.kernel.queue.enqueue("delete-data", {})
        self.assertEqual(task["status"], "blocked")
        self.assertIn("Irreversible", task["blockedReasons"][0])

        paid = self.kernel.queue.enqueue("video-generation", {"paidProvider": True})
        self.assertEqual(paid["status"], "blocked")

    def test_self_healing_requeues_stale_running_tasks(self) -> None:
        task = self.kernel.queue.enqueue("health-check", {})
        claimed = self.kernel.queue.claim_next()
        self.assertEqual(claimed["id"], task["id"])
        registry = self.kernel.queue.load()
        for item in registry["tasks"]:
            if item["id"] == task["id"]:
                item["startedAt"] = "2000-01-01T00:00:00"
        self.kernel.queue.save(registry)
        healed = self.kernel.self_healing.run()
        self.assertEqual(healed["healedTasks"], [task["id"]])
        status = self.kernel.queue.status()
        self.assertEqual(status["byStatus"]["queued"], 1)

    def test_plugin_manifest_validation_and_scan(self) -> None:
        plugin_dir = self.kernel.paths.plugins_dir / "sample"
        plugin_dir.mkdir(parents=True)
        manifest = {
            "id": "sample",
            "name": "Sample Plugin",
            "version": "1.0.0",
            "capabilities": ["image"],
            "entryPoint": "plugin.py",
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
        status = self.kernel.plugins.status()
        self.assertEqual(status["installed"], 1)
        self.assertTrue(status["plugins"][0]["validation"]["ok"])

    def test_backup_and_confirmed_restore(self) -> None:
        self.kernel.ensure_initialized()
        self.kernel.knowledge.add_entry("Restore Test", "This entry should survive restore.", ["test"])
        backup = self.kernel.backups.create(label="unit")
        self.assertTrue(Path(backup["path"]).exists())

        self.kernel.knowledge.add_entry("After Backup", "This entry should be rolled back.", ["test"])
        restored = self.kernel.backups.restore(Path(backup["path"]), confirm=True)
        self.assertTrue(Path(restored["safetyBackup"]).exists())
        entries = self.kernel.knowledge.load()["entries"]
        titles = [entry["title"] for entry in entries]
        self.assertIn("Restore Test", titles)
        self.assertNotIn("After Backup", titles)

    def test_support_package_excludes_private_media(self) -> None:
        self.kernel.ensure_initialized()
        photo = self.kernel.paths.workspaces / "default" / "assets" / "private.jpg"
        photo.write_bytes(b"private")
        package = self.kernel.support_packages.create({"config": {"api_key": "secret"}, "photo": str(photo)})
        self.assertTrue(Path(package["path"]).exists())
        import zipfile

        with zipfile.ZipFile(package["path"]) as zipf:
            names = zipf.namelist()
            self.assertNotIn("private.jpg", " ".join(names))
            status = json.loads(zipf.read("status.json").decode("utf-8"))
            self.assertEqual(status["config"]["api_key"], "[REDACTED]")

    def test_rest_api_health(self) -> None:
        server = self.kernel.serve("127.0.0.1", 0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["overall"], "PASS")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_self_test_passes(self) -> None:
        result = self.kernel.self_test()
        self.assertEqual(result["overall"], "PASS")


if __name__ == "__main__":
    unittest.main()
