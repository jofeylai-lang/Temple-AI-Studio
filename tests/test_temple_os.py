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
        self.assertIn("agents", payload)
        self.assertIn("applications", payload)
        self.assertIn("userProfiles", payload)
        self.assertTrue(self.kernel.paths.config.exists())
        self.assertTrue((self.kernel.paths.workspaces / "default" / "workspace.json").exists())
        status = self.kernel.status()
        self.assertEqual(status["version"], "0.1.0")
        self.assertGreaterEqual(status["providers"]["enabled"], 3)
        self.assertEqual(status["multiUser"]["mode"], "single-user-local")
        self.assertEqual(status["cloudSync"]["allowed"], False)

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

    def test_job_queue_dependencies_cancel_resume_and_parallel(self) -> None:
        first = self.kernel.queue.enqueue("prompt-optimize", {"prompt": "Temple product"}, priority=20)
        second = self.kernel.queue.enqueue("provider-simulate", {"capability": "image", "prompt": "Temple product"}, priority=90, depends_on=[first["id"]])
        result = self.kernel.worker.run_once()
        self.assertEqual(result["task"]["id"], first["id"])
        result = self.kernel.worker.run_once()
        self.assertEqual(result["task"]["id"], second["id"])

        cancelled = self.kernel.queue.enqueue("health-check", {})
        self.assertEqual(self.kernel.queue.cancel(cancelled["id"])["status"], "cancelled")
        self.assertEqual(self.kernel.queue.resume(cancelled["id"])["status"], "queued")
        graph = self.kernel.queue.dependency_graph()
        self.assertGreaterEqual(len(graph["nodes"]), 3)
        batch = self.kernel.queue.run_parallel(self.kernel.worker, limit=2)
        self.assertGreaterEqual(batch["processed"], 1)

    def test_ai_agent_plan_queue_and_collaboration(self) -> None:
        plan = self.kernel.agents.create_plan("請用繁體中文產生一支產品短影片", app_id="temple-product-video-generator")
        self.assertEqual(plan["status"], "planned")
        self.assertGreaterEqual(len(plan["steps"]), 5)

        queued = self.kernel.agents.enqueue_plan(plan["id"])
        self.assertEqual(queued["status"], "queued")
        for _task_id in queued["taskIds"]:
            result = self.kernel.worker.run_once()
            self.assertEqual(result["task"]["status"], "completed")
        runs = self.kernel.agents.runs()["runs"]
        completed = next(item for item in runs if item["id"] == plan["id"])
        self.assertEqual(completed["status"], "completed")

        session = self.kernel.collaboration.start("建立神殿影片專案", app_id="temple-product-video-generator")
        self.assertEqual(session["status"], "planned")
        self.assertGreaterEqual(len(session["participants"]), 5)

    def test_business_rules_block_destructive_and_paid_tasks(self) -> None:
        task = self.kernel.queue.enqueue("delete-data", {})
        self.assertEqual(task["status"], "blocked")
        self.assertIn("Irreversible", task["blockedReasons"][0])

        paid = self.kernel.queue.enqueue("video-generation", {"paidProvider": True})
        self.assertEqual(paid["status"], "blocked")

    def test_application_user_download_update_and_future_contracts(self) -> None:
        apps = self.kernel.applications.status()
        self.assertEqual(apps["production"], 1)
        self.assertIsNotNone(self.kernel.applications.get("temple-product-video-generator"))

        profile = self.kernel.user_profiles.active()
        self.assertEqual(profile["language"], "zh-TW")

        download = self.kernel.downloads.request("remote-model", "https://example.com/model.gguf", "llm")
        self.assertEqual(download["status"], "blocked")

        manifest = self.root / "update-manifest.json"
        manifest.write_text(json.dumps({"version": "0.1.1"}), encoding="utf-8")
        update = self.kernel.updates.plan_local_update("0.1.1", manifest)
        self.assertTrue(Path(update["preUpdateBackup"]).exists())

        self.assertEqual(self.kernel.mobile_api.status()["status"], "local-contract-ready")
        with self.assertRaises(PermissionError):
            self.kernel.cloud_sync.request_sync()
        self.assertEqual(self.kernel.multi_user.status()["mode"], "single-user-local")

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
        self.assertTrue(self.kernel.plugins.configure("sample", {"mode": "test"})["lifecycle"]["configured"])
        self.assertTrue(self.kernel.plugins.load_plugin("sample")["lifecycle"]["loaded"])
        self.assertFalse(self.kernel.plugins.set_enabled("sample", False)["lifecycle"]["enabled"])

    def test_local_capability_infrastructure(self) -> None:
        workflow = self.kernel.workflow_editor.clone_template("template.product-video", "Unit Workflow")
        self.assertTrue(workflow["validation"]["ok"])

        memory = self.kernel.agent_memory.remember("intent-analyst", "preference", {"tone": "commercial"})
        self.assertEqual(memory["key"], "preference")
        self.assertEqual(len(self.kernel.agent_memory.recall("intent-analyst", "preference")), 1)

        optimized = self.kernel.prompt_lab.optimize("Temple product", "comfyui-local")
        self.assertIn("commercial-ready", optimized["optimized"])
        compared = self.kernel.prompt_lab.compare("short", optimized["optimized"])
        self.assertEqual(compared["winner"], "b")

        image = self.kernel.provider_simulator.generate("image", "Temple product")
        self.assertTrue(Path(image["artifact"]).exists())
        bench = self.kernel.model_sandbox.run_benchmark("mock-model", "video", ["A", "B"])
        self.assertEqual(bench["prompts"], 2)

        project = self.kernel.projects.create("Workspace Unit", "temple-product-video-generator")
        snapshot = self.kernel.workspace_system.snapshot(project["id"], "unit")
        self.assertEqual(snapshot["projectId"], project["id"])
        clone = self.kernel.workspace_system.clone_template(project["id"], "Workspace Clone")
        self.assertEqual(clone["metadata"]["clonedFrom"], project["id"])

        knowledge = self.kernel.structured_knowledge.add("product", "Incense", {"material": "wood"}, ["product"])
        self.assertEqual(knowledge["fields"]["material"], "wood")

        sdk = self.kernel.developer_sdk.generate_docs()
        self.assertTrue(Path(sdk["docsPath"]).exists())

        test_run = self.kernel.testing.stress_queue(self.kernel.queue, count=2)
        self.assertEqual(test_run["overall"], "PASS")

        self.kernel.performance.cache_put("unit", {"value": 1})
        self.assertEqual(self.kernel.performance.cache_get("unit"), {"value": 1})
        self.assertEqual(self.kernel.performance.cleanup()["removed"], 0)

        env = self.kernel.packaging.environment_check()
        self.assertEqual(env["overall"], "PASS")
        portable = self.kernel.packaging.create_portable_manifest()
        self.assertTrue(Path(portable["manifestPath"]).exists())

        diagnostics = self.kernel.production_readiness.startup_diagnostics()
        self.assertEqual(diagnostics["overall"], "PASS")
        self.assertTrue(self.kernel.production_readiness.set_safe_mode(True)["safeMode"])
        self.assertIn("Temple AI Studio", self.kernel.launcher.html(self.kernel.status()))

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

    def test_rest_api_agent_plan_and_mobile_status(self) -> None:
        server = self.kernel.serve("127.0.0.1", 0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/agents/plan",
                data=json.dumps({"request": "請產生影片"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                plan = json.loads(response.read().decode("utf-8"))
            self.assertEqual(plan["status"], "planned")

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/mobile/v1/status", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["mobile"]["status"], "local-contract-ready")

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Temple AI Studio", html)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_self_test_passes(self) -> None:
        result = self.kernel.self_test()
        self.assertEqual(result["overall"], "PASS")


if __name__ == "__main__":
    unittest.main()
