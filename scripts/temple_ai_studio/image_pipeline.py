from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from temple_ai_studio.asset_manager import AssetManager
from temple_ai_studio.emma_core import EmmaCore
from temple_ai_studio.prompt_translation_engine import translate_prompts
from temple_ai_studio.quality_analyzer import evaluate_image, evaluate_project
from temple_ai_studio.storyboard_engine import build_storyboard


IMAGE_PIPELINE_SCHEMA = "temple-ai-studio.image-pipeline.v1"
IMAGE_PIPELINE_VERSION = "1.0.0"
FRAME_SIZE = (1080, 1920)
DEFAULT_PROVIDER = "local_commercial_composite"
MAX_RETRIES = 2


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\mingliu.ttc", r"C:\Windows\Fonts\arial.ttf"]:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def fit_contain(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = min(size[0] / img.width, size[1] / img.height)
    return img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in str(text or ""):
        trial = current + char
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:3]


class LocalCommercialCompositeProvider:
    name = DEFAULT_PROVIDER

    def generate(
        self,
        scene: dict[str, Any],
        storyboard_scene: dict[str, Any],
        prompt_bundle: dict[str, Any],
        product: dict[str, Any],
        source_image: Path,
        output_path: Path,
        seed: int,
        attempt: int,
    ) -> dict[str, Any]:
        random.seed(seed + attempt)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source_image) as raw:
            source = raw.convert("RGB")
            background = fit_cover(source, FRAME_SIZE).filter(ImageFilter.GaussianBlur(20 - min(attempt, 1) * 4))
            warm = Image.new("RGB", FRAME_SIZE, self._background_tint(scene.get("purpose", "")))
            canvas = Image.blend(background, warm, 0.42 if attempt == 0 else 0.34)
            product_box = self._product_box(scene.get("purpose", ""), attempt)
            product_img = fit_contain(source, (product_box[2] - product_box[0], product_box[3] - product_box[1]))
        draw = ImageDraw.Draw(canvas)
        self._draw_commercial_layout(draw, canvas, product_img, product_box, scene, storyboard_scene, product, attempt)
        canvas.save(output_path, quality=95)
        return {
            "provider": self.name,
            "seed": seed,
            "attempt": attempt,
            "output": str(output_path),
            "negativePrompt": prompt_bundle.get("negative", ""),
            "model": "local-pil-commercial-composite-v1",
            "width": FRAME_SIZE[0],
            "height": FRAME_SIZE[1],
            "createdAt": now_iso(),
        }

    def _background_tint(self, purpose: str) -> str:
        if purpose == "Product Features":
            return "#f5efe4"
        if purpose == "Spiritual Value":
            return "#f3eadc"
        if purpose == "Call To Action":
            return "#f7f5ef"
        if purpose == "Ending":
            return "#eef3ef"
        return "#f7f3ec"

    def _product_box(self, purpose: str, attempt: int) -> tuple[int, int, int, int]:
        if purpose == "Hook":
            return (170, 410, 910, 1080)
        if purpose == "Product Features":
            return (115, 360, 965, 1130)
        if purpose == "Spiritual Value":
            return (155, 390, 925, 1110)
        if purpose == "Call To Action":
            return (130, 330, 950, 1110)
        if purpose == "Ending":
            return (185, 360, 895, 1050)
        return (140, 360, 940, 1100)

    def _draw_commercial_layout(
        self,
        draw: ImageDraw.ImageDraw,
        canvas: Image.Image,
        product_img: Image.Image,
        product_box: tuple[int, int, int, int],
        scene: dict[str, Any],
        storyboard_scene: dict[str, Any],
        product: dict[str, Any],
        attempt: int,
    ) -> None:
        title_font = get_font(54)
        scene_font = get_font(30)
        subtitle_font = get_font(62 if len(scene.get("subtitle", "")) <= 12 else 52)
        small_font = get_font(28)
        product_x = product_box[0] + ((product_box[2] - product_box[0]) - product_img.width) // 2
        product_y = product_box[1] + ((product_box[3] - product_box[1]) - product_img.height) // 2
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle((product_x - 34, product_y - 34, product_x + product_img.width + 34, product_y + product_img.height + 34), radius=42, fill=(0, 0, 0, 46))
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB"))
        draw.rounded_rectangle(
            (product_x - 26, product_y - 26, product_x + product_img.width + 26, product_y + product_img.height + 26),
            radius=36,
            fill="#ffffff",
            outline="#d6c4a8",
            width=4,
        )
        canvas.paste(product_img, (product_x, product_y))
        draw.text((76, 100), product.get("name", "Temple Product"), fill="#17231f", font=title_font)
        draw.text((80, 168), storyboard_scene.get("shotType", scene.get("purpose", "")), fill="#7a6245", font=scene_font)
        safe_box = (64, 1410, 1016, 1736)
        draw.rounded_rectangle(safe_box, radius=30, fill="#17231f")
        draw.rounded_rectangle((safe_box[0] + 10, safe_box[1] + 10, safe_box[2] - 10, safe_box[3] - 10), radius=24, outline="#d9b36c", width=2)
        lines = wrap_text(draw, scene.get("subtitle", ""), subtitle_font, 860)
        y = safe_box[1] + 48
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=subtitle_font)
            draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=subtitle_font)
            y += 78
        draw.rounded_rectangle((740, 1780, 1022, 1848), radius=14, fill="#245c4f")
        draw.text((770, 1797), "Temple AI Studio", fill="#ffffff", font=small_font)


class ImagePipeline:
    def __init__(self, provider: str = DEFAULT_PROVIDER, max_retries: int = MAX_RETRIES):
        self.provider_name = provider
        self.max_retries = max_retries
        self.provider = LocalCommercialCompositeProvider()

    def run(self, project: dict[str, Any], product: dict[str, Any], project_dir: Path, emma_root: Path | None = None) -> dict[str, Any]:
        asset_manager = AssetManager(Path(project_dir), project["id"])
        emma_core = EmmaCore(emma_root)
        emma_status = emma_core.initialize()
        product_assets = asset_manager.register_product_assets(product)
        source_images = [Path(item["path"]) for item in product_assets if Path(item["path"]).exists()]
        if not source_images:
            raise RuntimeError("No product reference images are available for visual generation.")
        storyboard = build_storyboard(project, product)
        provider_prompts = translate_prompts(project, storyboard, product, ["comfyui", "flux", "sdxl", "wan", "ltx", "kling", "runway", "openai", "future"])
        prompt_by_scene = {item["sceneId"]: item["providers"] for item in provider_prompts["scenes"]}
        story_by_scene = {item["id"]: item for item in storyboard["scenes"]}
        generated = []
        quality_reports = []
        history = []
        for index, scene in enumerate(project.get("scenes", []) or []):
            source = source_images[index % len(source_images)]
            seed = self._stable_seed(project["id"], scene["id"], scene.get("version", 1))
            prompt_bundle = prompt_by_scene[scene["id"]]["openai"]
            story_scene = story_by_scene[scene["id"]]
            require_emma = scene_requires_emma(scene)
            emma_references = emma_core.select_references("openai", generation_type="image", require_emma=require_emma)
            if require_emma and emma_references["overall"] == "BLOCKED":
                raise RuntimeError(f"Emma references are required but unavailable for scene: {scene['id']}")
            best_record = None
            best_quality = None
            best_emma = None
            for attempt in range(self.max_retries + 1):
                output = asset_manager.generated_root / f"{scene['order']:02d}-{scene['id']}-v{scene.get('version', 1)}-a{attempt}.png"
                generation = self.provider.generate(scene, story_scene, prompt_bundle, product, source, output, seed, attempt)
                emma_eval = emma_core.evaluate_generation(output, scene=scene, provider="openai", require_emma=require_emma)
                quality = evaluate_image(output, scene, prompt_bundle, emma_eval)
                asset = asset_manager.register(
                    output,
                    asset_type="generated-image",
                    role="scene-visual",
                    scene_id=scene["id"],
                    provider=self.provider.name,
                    source=str(source),
                    metadata={
                        "seed": seed,
                        "attempt": attempt,
                        "qualityScore": quality["score"],
                        "qualityOverall": quality["overall"],
                        "emmaConsistency": emma_eval,
                    },
                )
                history.append({"sceneId": scene["id"], "attempt": attempt, "assetId": asset["id"], "quality": quality, "emma": emma_eval})
                if best_quality is None or quality["score"] > best_quality["score"]:
                    best_record = {**generation, "asset": asset}
                    best_quality = quality
                    best_emma = emma_eval
                if quality["overall"] == "PASS":
                    break
            scene["storyboard"] = story_scene
            scene["providerPrompts"] = prompt_by_scene[scene["id"]]
            scene["emmaCore"] = {
                "required": require_emma,
                "referenceSelection": emma_references,
                "consistency": best_emma,
            }
            scene["generatedImagePath"] = best_record["output"] if best_record else ""
            scene["visualQuality"] = best_quality
            scene["visualStatus"] = best_quality["overall"] if best_quality else "FAIL"
            generated.append(best_record)
            quality_reports.append(best_quality)
        project_quality = evaluate_project([report for report in quality_reports if report])
        report = {
            "schema": IMAGE_PIPELINE_SCHEMA,
            "version": IMAGE_PIPELINE_VERSION,
            "createdAt": now_iso(),
            "projectId": project["id"],
            "provider": self.provider.name,
            "storyboard": storyboard,
            "providerPrompts": provider_prompts,
            "emmaCore": {
                "status": emma_status,
                "knowledgeProfile": emma_core.get_context("future", require_emma=False).get("knowledge"),
            },
            "generatedImages": generated,
            "quality": project_quality,
            "history": history,
            "assetIndex": str(asset_manager.write()),
        }
        report_path = Path(project_dir) / "visual-pipeline-report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _stable_seed(self, *parts: Any) -> int:
        value = "|".join(str(part) for part in parts)
        return abs(hash(value)) % 2_147_483_647


def scene_requires_emma(scene: dict[str, Any]) -> bool:
    content = " ".join(
        str(scene.get(key, "")) for key in ["narration", "subtitle", "prompt", "visualDescription"]
    ).lower()
    return "emma" in content or "艾瑪" in content


def run_image_pipeline(
    project: dict[str, Any],
    product: dict[str, Any],
    project_dir: Path,
    provider: str = DEFAULT_PROVIDER,
    emma_root: Path | None = None,
) -> dict[str, Any]:
    return ImagePipeline(provider=provider).run(project, product, project_dir, emma_root=emma_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Image Pipeline.")
    parser.add_argument("--project-json", required=True)
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project = json.loads(Path(args.project_json).read_text(encoding="utf-8-sig"))
    product = json.loads(Path(args.product_json).read_text(encoding="utf-8-sig"))
    report = run_image_pipeline(project, product, Path(args.project_dir))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["quality"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
