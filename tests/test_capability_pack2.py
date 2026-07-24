from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.prompt_translation_engine import SUPPORTED_PROVIDERS, translate_prompts
from temple_ai_studio.quality_analyzer import evaluate_image
from temple_ai_studio.script_engine import generate_video_script_package
from temple_ai_studio.storyboard_engine import build_storyboard


def make_product_image(path: Path) -> None:
    image = Image.new("RGB", (1200, 1600), "#f4ead9")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((350, 360, 850, 1150), radius=48, fill="#ffffff", outline="#b8945f", width=8)
    draw.ellipse((460, 500, 740, 780), fill="#d9b36c")
    draw.rectangle((515, 760, 685, 1050), fill="#2f6f61")
    draw.text((375, 1230), "Temple Energy Candle", fill="#17231f")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


class CapabilityPack2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_path = self.root / "product.png"
        make_product_image(self.image_path)
        self.product = {
            "id": "product-test",
            "name": "Temple Energy Candle",
            "category": "香氛蠟燭",
            "description": "適合睡前與靜心使用的手作香氛蠟燭。",
            "sellingPoint": "手工製作、氣味溫柔、包裝精緻。",
            "spiritualInfo": "象徵祝福與安定，不做誇大承諾。",
            "targetAudience": "想建立日常儀式感的顧客",
            "materials": [{"id": "mat-1", "fileName": "product.png", "path": str(self.image_path), "role": "main-product"}],
        }
        self.project = generate_video_script_package(
            self.product,
            {"requirement": "請做一支溫柔、有儀式感的 IG Reels。", "platform": "Instagram Reels", "duration": 24},
            "project-test",
        )
        self.project["id"] = "project-test"
        self.project["projectDir"] = str(self.root / "project")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_storyboard_generates_scene_planning(self) -> None:
        storyboard = build_storyboard(self.project, self.product)
        self.assertEqual(storyboard["quality"]["overall"], "PASS")
        self.assertEqual(len(storyboard["scenes"]), 6)
        self.assertIn("shotType", storyboard["scenes"][0])
        self.assertIn("composition", storyboard["scenes"][0])

    def test_prompt_translation_generates_provider_adapters(self) -> None:
        storyboard = build_storyboard(self.project, self.product)
        prompts = translate_prompts(self.project, storyboard, self.product)
        self.assertEqual(set(prompts["providers"]), set(SUPPORTED_PROVIDERS))
        first = prompts["scenes"][0]["providers"]
        self.assertIn("comfyui", first)
        self.assertIn("negative", first["ltx"])
        self.assertIn("Preserve product appearance", first["openai"]["positive"])

    def test_image_pipeline_generates_assets_and_quality(self) -> None:
        report = run_image_pipeline(self.project, self.product, Path(self.project["projectDir"]), emma_root=self.root)
        self.assertEqual(report["quality"]["overall"], "PASS")
        self.assertEqual(len(report["generatedImages"]), 6)
        self.assertTrue(Path(report["assetIndex"]).exists())
        for scene in self.project["scenes"]:
            self.assertTrue(Path(scene["generatedImagePath"]).exists())
            self.assertEqual(scene["visualQuality"]["overall"], "PASS")

    def test_quality_analyzer_scores_generated_image(self) -> None:
        report = run_image_pipeline(self.project, self.product, Path(self.project["projectDir"]), emma_root=self.root)
        scene = self.project["scenes"][0]
        quality = evaluate_image(Path(scene["generatedImagePath"]), scene, scene["providerPrompts"]["openai"])
        self.assertEqual(quality["overall"], "PASS")
        self.assertGreaterEqual(quality["score"], 0.78)
        self.assertLessEqual(quality["score"], 1.0)
        self.assertIn("sharpness", quality["scores"])
        self.assertIn("subtitleContrast", quality["scores"])
        self.assertGreaterEqual(quality["scores"]["productVisibility"], 0.72)
        self.assertEqual(report["history"][0]["attempt"], 0)


if __name__ == "__main__":
    unittest.main()
