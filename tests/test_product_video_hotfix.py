from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
import uuid
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "apps" / "temple-product-video-generator" / "server.py"


def load_server(data_root: Path):
    os.environ["TPVG_DATA_DIR"] = str(data_root)
    os.environ["TEMPLE_PRODUCTION_DATA_ROOT"] = str(data_root / "production")
    name = f"tpvg_hotfix_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def image_payload(name: str = "product.png") -> dict:
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), "#66806f").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "name": name,
        "type": "image/png",
        "kind": "image",
        "data": f"data:image/png;base64,{encoded}",
    }


class ProductVideoHotfixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = load_server(self.root / "data")

    def tearDown(self) -> None:
        for thread in list(self.server.ACTIVE_JOB_THREADS.values()):
            thread.join(timeout=5)
        self.temp.cleanup()

    def product_payload(self, name: str = "平安燭") -> dict:
        return {
            "name": name,
            "category": "祈福用品",
            "description": "日常祈福使用",
            "sellingPoint": "溫暖、穩定、適合送禮",
            "productInfo": "單入",
            "spiritualInfo": "平安祝福",
            "targetAudience": "一般大眾",
            "tags": "平安、祈福",
            "seoKeywords": "祈福燭, 神殿商品",
        }

    def test_fresh_database_health_and_schema(self) -> None:
        health = self.server.database_health()
        self.assertTrue(health["exists"])
        self.assertTrue(health["readable"])
        self.assertTrue(health["writable"])
        self.assertEqual(health["schemaVersion"], 2)
        self.assertEqual(health["productCount"], 0)
        self.assertEqual(health["apiHealth"], "正常")

    def test_schema_one_migrates_without_losing_products(self) -> None:
        self.server.ensure_dirs()
        legacy = {
            "schemaVersion": 1,
            "products": [{"id": "product-old", **self.product_payload()}],
            "projects": [],
            "errors": [],
        }
        self.server.DB_PATH.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
        db = self.server.load_db()
        self.assertEqual(db["schemaVersion"], 2)
        self.assertEqual(db["products"][0]["id"], "product-old")
        self.assertEqual(db["jobs"], [])
        self.assertTrue((self.server.BACKUP_ROOT / "migrations").exists())

    def test_corrupt_database_is_backed_up_and_recovered(self) -> None:
        self.server.ensure_dirs()
        self.server.DB_PATH.write_text("{not-json", encoding="utf-8")
        db = self.server.load_db()
        self.assertEqual(db["schemaVersion"], 2)
        self.assertTrue(self.server.DATABASE_RECOVERY_STATE["recovered"])
        backup = Path(self.server.DATABASE_RECOVERY_STATE["backupPath"])
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(encoding="utf-8"), "{not-json")

    def test_duplicate_product_names_keep_stable_unique_ids(self) -> None:
        first = self.server.create_product(self.product_payload())
        second = self.server.create_product(self.product_payload())
        self.assertNotEqual(first["id"], second["id"])
        persisted = self.server.load_db()["products"]
        self.assertEqual(len(persisted), 2)
        self.assertEqual({item["name"] for item in persisted}, {"平安燭"})

    def test_product_material_persists_and_duplicate_is_rejected(self) -> None:
        product = self.server.create_product(self.product_payload())
        result = self.server.add_materials(product["id"], [image_payload()])
        self.assertEqual(len(result["materials"]), 1)
        persisted = self.server.find_item(self.server.load_db()["products"], product["id"])
        self.assertEqual(len(persisted["materials"]), 1)
        with self.assertRaisesRegex(ValueError, "重複"):
            self.server.add_materials(product["id"], [image_payload()])

    def test_text_only_mode_accepts_zero_products_and_zero_photos(self) -> None:
        validation = self.server.validate_project_submission(
            {
                "mode": "text-only",
                "duration": 20,
                "requirement": "請製作一支溫暖的繁體中文影片。",
            }
        )
        self.assertEqual(validation["mode"], "text-only")
        self.assertIsNone(validation["product"])

    def test_product_mode_reports_missing_product_and_materials(self) -> None:
        with self.assertRaises(ValueError) as missing_product:
            self.server.validate_project_submission(
                {"mode": "product", "duration": 20, "requirement": "商品影片"}
            )
        self.assertIn("productId", missing_product.exception.field_errors)

        product = self.server.create_product(self.product_payload())
        with self.assertRaises(ValueError) as missing_material:
            self.server.validate_project_submission(
                {
                    "mode": "product",
                    "productId": product["id"],
                    "duration": 20,
                    "requirement": "商品影片",
                }
            )
        self.assertIn("materials", missing_material.exception.field_errors)

    def test_duration_conflict_uses_ui_duration(self) -> None:
        conflict = self.server.duration_conflict(
            {"duration": 30, "requirement": "請製作 15 秒的短片"}
        )
        self.assertEqual(conflict["requestDuration"], 15)
        self.assertEqual(conflict["selectedDuration"], 30)

        content = self.server.generate_content(
            self.server.inline_product({"requirement": "請製作 6 秒的短片"}),
            {"duration": 8, "requirement": "請製作 6 秒的短片"},
            "duration-source-of-truth",
        )
        self.assertEqual(content["duration"], 8)
        self.assertAlmostEqual(
            sum(float(scene["duration"]) for scene in content["scenes"]),
            8,
            places=2,
        )

    def test_idempotency_creates_exactly_one_job(self) -> None:
        self.server.start_job = lambda _job_id: None
        payload = {
            "action": "create-project",
            "mode": "text-only",
            "duration": 20,
            "requirement": "純文字影片",
            "idempotencyKey": "same-submit",
        }
        first, duplicate_first = self.server.create_job(payload)
        second, duplicate_second = self.server.create_job(payload)
        self.assertFalse(duplicate_first)
        self.assertTrue(duplicate_second)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.server.load_db()["jobs"]), 1)

    def test_background_job_completion_is_persisted(self) -> None:
        original_create = self.server.create_project_record
        original_render = self.server.render_project

        def fake_create(payload, validation=None):
            project = {
                "id": self.server.new_id("project"),
                "productId": "",
                "productName": "純文字測試",
                "mode": "text-only",
                "inlineProduct": self.server.inline_product(payload),
                "status": "Planning",
                "createdAt": self.server.now_iso(),
                "updatedAt": self.server.now_iso(),
                "outputDir": str(self.server.EXPORT_ROOT / "fake"),
                "projectDir": str(self.server.PROJECT_ROOT / "fake"),
                "scenes": [],
                "errors": [],
            }
            with self.server.DB_LOCK:
                db = self.server.load_db()
                db["projects"].append(project)
                self.server.save_db(db)
            return project

        def fake_render(project_id, preview, progress_callback=None):
            for stage, progress in [("images", 44), ("video", 66), ("render", 96)]:
                progress_callback(stage, progress, f"{stage} complete")
            with self.server.DB_LOCK:
                db = self.server.load_db()
                project = self.server.find_item(db["projects"], project_id)
                project["status"] = "Ready for Preview"
                project["previewVideo"] = "/api/files/fake.mp4"
                self.server.save_db(db)
                return project

        self.server.create_project_record = fake_create
        self.server.render_project = fake_render
        try:
            job, _ = self.server.create_job(
                {
                    "action": "create-project",
                    "mode": "text-only",
                    "duration": 20,
                    "requirement": "純文字影片",
                    "idempotencyKey": "background-complete",
                }
            )
            for _ in range(50):
                current = self.server.get_job(job["id"])
                if current["status"] == "completed":
                    break
                time.sleep(0.02)
            self.assertEqual(current["status"], "completed")
            self.assertEqual(current["progress"], 100)
            self.assertTrue(current["result"]["previewVideo"])
        finally:
            self.server.create_project_record = original_create
            self.server.render_project = original_render

    def test_cancel_and_retry_are_recoverable(self) -> None:
        self.server.start_job = lambda _job_id: None
        job, _ = self.server.create_job(
            {
                "action": "create-project",
                "mode": "text-only",
                "duration": 20,
                "requirement": "取消測試",
                "idempotencyKey": "cancel-test",
            }
        )
        cancelled = self.server.cancel_job(job["id"])
        self.assertEqual(cancelled["status"], "cancelling")
        with self.server.DB_LOCK:
            db = self.server.load_db()
            stored = self.server.find_item(db["jobs"], job["id"])
            stored["status"] = "cancelled"
            self.server.save_db(db)
        retried = self.server.retry_job(job["id"])
        self.assertEqual(retried["status"], "queued")
        self.assertEqual(retried["retryCount"], 1)

    def test_http_submission_returns_immediately_and_disables_cache(self) -> None:
        self.server.start_job = lambda _job_id: None
        httpd = self.server.ThreadingHTTPServer(("127.0.0.1", 0), self.server.AppHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            payload = json.dumps(
                {
                    "action": "create-project",
                    "mode": "text-only",
                    "duration": 20,
                    "requirement": "立即回應測試",
                    "idempotencyKey": "http-fast-submit",
                },
                ensure_ascii=False,
            ).encode("utf-8")
            request = urllib.request.Request(
                f"http://127.0.0.1:{httpd.server_port}/api/jobs",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            started = time.perf_counter()
            with urllib.request.urlopen(request, timeout=3) as response:
                result = json.loads(response.read().decode("utf-8"))
                elapsed = time.perf_counter() - started
                self.assertEqual(response.status, 202)
                self.assertIn("no-store", response.headers["Cache-Control"])
            self.assertLess(elapsed, 1.0)
            self.assertEqual(result["job"]["status"], "queued")
            self.assertTrue(result["job"]["id"])
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_resume_pending_job_after_restart(self) -> None:
        self.server.start_job = lambda _job_id: None
        job, _ = self.server.create_job(
            {
                "action": "create-project",
                "mode": "text-only",
                "duration": 20,
                "requirement": "重啟恢復測試",
                "idempotencyKey": "resume-test",
            }
        )
        resumed = []
        self.server.start_job = resumed.append
        self.server.resume_pending_jobs()
        self.assertEqual(resumed, [job["id"]])
        current = self.server.get_job(job["id"])
        self.assertEqual(current["status"], "queued")
        self.assertIn("自動恢復", current["message"])

    def test_failure_guidance_covers_optional_tools(self) -> None:
        self.assertIn("FFmpeg", self.server.suggested_action("FFmpeg unavailable"))
        self.assertIn("ComfyUI", self.server.suggested_action("ComfyUI connection failed"))
        self.assertIn("聲音", self.server.suggested_action("TTS 聲音失敗"))

    def test_job_stage_history_is_persisted(self) -> None:
        self.server.start_job = lambda _job_id: None
        job, _ = self.server.create_job(
            {
                "action": "create-project",
                "mode": "text-only",
                "duration": 20,
                "requirement": "進度歷史測試",
                "idempotencyKey": "history-test",
            }
        )
        self.server.update_job(
            job["id"],
            status="running",
            stage="images",
            progress=44,
            message="正在建立影像。",
        )
        current = self.server.get_job(job["id"])
        self.assertEqual(current["stageHistory"][-1]["stage"], "images")
        self.assertEqual(current["stageHistory"][-1]["progress"], 44)

    def test_missing_ffmpeg_fails_with_recovery_guidance(self) -> None:
        product = self.server.create_product(self.product_payload())
        self.server.add_materials(product["id"], [image_payload()])
        self.server.save_config(
            {
                "ffmpegPath": str(self.root / "missing-ffmpeg.exe"),
                "providerMode": "local-first",
            }
        )
        self.server.is_retryable_failure = lambda _message: False
        self.server.start_job = self.server.run_job
        job, _ = self.server.create_job(
            {
                "action": "create-project",
                "mode": "product",
                "productId": product["id"],
                "duration": 20,
                "requirement": "FFmpeg 失敗測試",
                "idempotencyKey": "missing-ffmpeg",
            }
        )
        current = self.server.get_job(job["id"])
        self.assertEqual(current["status"], "failed")
        self.assertIn("FFmpeg", current["error"]["reason"])
        self.assertIn("FFmpeg", current["error"]["suggestedAction"])

    def test_comfyui_unavailable_is_reported_without_blocking_local_mode(self) -> None:
        health = self.server.comfyui_health("http://127.0.0.1:9")
        self.assertFalse(health["connected"])
        self.assertIn("ComfyUI", health["message"])

    def test_production_launcher_uses_available_temple_os_port(self) -> None:
        launcher = (
            REPO_ROOT / "scripts" / "start_temple_ai_studio.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[int]$TempleOsPort = 8766", launcher)
        self.assertIn("-port $TempleOsPort", launcher)
        self.assertIn("Test-LocalPort -Port $TempleOsPort", launcher)


if __name__ == "__main__":
    unittest.main()
