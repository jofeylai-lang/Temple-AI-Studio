from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.script_engine import generate_video_script_package
from temple_ai_studio.video_intelligence import CameraMotionEngine, RenderingPipeline, run_video_generation_pipeline


def detect_ffmpeg() -> Path:
    candidates = [
        shutil.which("ffmpeg"),
        r"C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("FFmpeg is required for video intelligence tests.")


def make_product_image(path: Path) -> None:
    image = Image.new("RGB", (1200, 1600), "#f4ead9")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((350, 360, 850, 1150), radius=48, fill="#ffffff", outline="#b8945f", width=8)
    draw.ellipse((460, 500, 740, 780), fill="#d9b36c")
    draw.rectangle((515, 760, 685, 1050), fill="#2f6f61")
    draw.text((375, 1230), "Temple Energy Candle", fill="#17231f")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


class VideoIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ffmpeg = detect_ffmpeg()
        self.product_image = self.root / "product.png"
        make_product_image(self.product_image)
        self.product = {
            "id": "product-video-test",
            "name": "Temple Energy Candle",
            "category": "香氛蠟燭",
            "description": "適合睡前與靜心使用的手作香氛蠟燭。",
            "sellingPoint": "手工製作、氣味溫柔、包裝精緻。",
            "spiritualInfo": "象徵祝福與安定，不做誇大承諾。",
            "targetAudience": "想建立日常儀式感的顧客",
            "materials": [{"id": "mat-1", "fileName": "product.png", "path": str(self.product_image), "role": "main-product"}],
        }
        self.project = generate_video_script_package(
            self.product,
            {"requirement": "請做一支溫柔、有儀式感的 IG Reels。", "platform": "Instagram Reels", "duration": 18},
            "project-video-test",
        )
        self.project["id"] = "project-video-test"
        self.project["projectDir"] = str(self.root / "project")
        run_image_pipeline(self.project, self.product, Path(self.project["projectDir"]), emma_root=self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_camera_motion_plan_is_provider_neutral(self) -> None:
        plan = CameraMotionEngine().plan(self.project["scenes"][0])
        self.assertEqual(plan["overall"], "PASS")
        self.assertIn("zoomExpression", plan)
        self.assertIn("stability", plan)
        self.assertFalse(plan["usesFrameRandomness"])
        self.assertNotIn("sin(", plan["xExpression"])

    def test_rendering_retry_uses_fallback_codec(self) -> None:
        frame = Path(self.project["scenes"][0]["generatedImagePath"])
        output = self.root / "retry-test.mp4"
        renderer = RenderingPipeline(self.ffmpeg, codecs=["invalid_codec_for_retry", "mpeg4"])
        report = renderer.render_clip(frame, output, 2, CameraMotionEngine().plan(self.project["scenes"][0]))
        self.assertEqual(report["overall"], "PASS")
        self.assertTrue(output.exists())
        self.assertEqual(report["attempts"][0]["returnCode"] != 0, True)
        self.assertEqual(report["codec"], "mpeg4")
        self.assertIn("-b:v", report["videoArgs"])

    def test_still_only_video_is_rejected_as_slideshow(self) -> None:
        output_dir = self.root / "exports"
        report = run_video_generation_pipeline(self.project, self.product, output_dir, Path(self.project["projectDir"]), self.ffmpeg, preview=False)
        self.assertEqual(report["quality"]["overall"], "FAIL")
        self.assertTrue((output_dir / "final_video.mp4").exists())
        self.assertTrue((output_dir / "final_video_subtitled.mp4").exists())
        self.assertTrue((output_dir / "subtitles.srt").exists())
        self.assertTrue(report["quality"]["decode"]["metadata"]["audioLine"])
        failed = {check["name"] for check in report["quality"]["failedChecks"]}
        self.assertIn("unique-root-assets", failed)
        self.assertIn("real-motion-present", failed)
        for scene_report in report["sceneReports"]:
            self.assertEqual(scene_report["subtitle"]["overall"], "PASS")
            self.assertEqual(scene_report["render"]["overall"], "PASS")
            self.assertIn("videoArgs", scene_report["render"])
            self.assertIn(scene_report["lipSync"]["overall"], ["NOT_REQUIRED", "READY", "WAITING_FOR_AUDIO"])

    def test_distinct_real_video_scenes_pass_editorial_gate(self) -> None:
        colors = ["red", "green", "blue", "yellow", "magenta"]
        for index, scene in enumerate(self.project["scenes"][:5]):
            video = self.root / f"source-{index + 1}.mp4"
            result = subprocess.run(
                [
                    str(self.ffmpeg),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"testsrc2=size=360x640:rate=25:duration=2,drawbox=color={colors[index]}@0.35:t=fill",
                    "-c:v",
                    "mpeg4",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-1000:])
            scene["sourceVideoPath"] = str(video)
        output_dir = self.root / "real-motion-exports"
        report = run_video_generation_pipeline(
            self.project,
            self.product,
            output_dir,
            Path(self.project["projectDir"]),
            self.ffmpeg,
            preview=True,
        )
        self.assertEqual(report["quality"]["overall"], "PASS")
        self.assertEqual(report["quality"]["editorialMetrics"]["videoSceneCount"], 5)
        self.assertGreaterEqual(report["quality"]["editorialMetrics"]["uniqueRootSourceCount"], 5)
        progression = next(
            check
            for check in report["quality"]["checks"]
            if check["name"] == "meaningful-shot-progression"
        )
        self.assertTrue(progression["ok"])

    def test_requested_duration_is_preserved_in_rendered_video(self) -> None:
        short_package = generate_video_script_package(
            self.product,
            {
                "requirement": "請製作一支 8 秒的直式短影音。",
                "platform": "Instagram Reels",
                "duration": 8,
            },
            "project-duration-test",
        )
        self.project["duration"] = short_package["duration"]
        for scene, short_scene in zip(self.project["scenes"], short_package["scenes"]):
            scene["duration"] = short_scene["duration"]
            scene["start"] = short_scene["start"]
            scene["end"] = short_scene["end"]

        output_dir = self.root / "duration-exports"
        report = run_video_generation_pipeline(
            self.project,
            self.product,
            output_dir,
            Path(self.project["projectDir"]),
            self.ffmpeg,
            preview=True,
        )
        duration_check = next(
            check
            for check in report["quality"]["checks"]
            if check["name"] == "duration-target"
        )
        self.assertTrue(duration_check["ok"])
        self.assertAlmostEqual(duration_check["expectedSeconds"], 8, places=2)
        self.assertLessEqual(abs(duration_check["actualSeconds"] - 8), 0.25)


if __name__ == "__main__":
    unittest.main()
