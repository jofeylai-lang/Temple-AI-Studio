from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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
            source = self._enhance_product(source, attempt)
            background = fit_cover(source, FRAME_SIZE).filter(ImageFilter.GaussianBlur(16 - min(attempt, 1) * 3))
            warm = Image.new("RGB", FRAME_SIZE, self._background_tint(scene.get("purpose", "")))
            canvas = Image.blend(background, warm, 0.36 if attempt == 0 else 0.30)
            canvas = self._add_depth(canvas, scene.get("purpose", ""))
            product_box = self._product_box(scene.get("purpose", ""), attempt)
            product_img = fit_contain(source, (product_box[2] - product_box[0], product_box[3] - product_box[1]))
            product_img = self._enhance_product(product_img, attempt)
        draw = ImageDraw.Draw(canvas)
        self._draw_commercial_layout(draw, canvas, product_img, product_box, scene, storyboard_scene, product, attempt)
        canvas.save(output_path, optimize=True, quality=96)
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

    def _enhance_product(self, image: Image.Image, attempt: int) -> Image.Image:
        enhanced = ImageEnhance.Color(image).enhance(1.06)
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1.08 + min(attempt, 1) * 0.04)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.28 + min(attempt, 1) * 0.12)
        return enhanced

    def _add_depth(self, canvas: Image.Image, purpose: str) -> Image.Image:
        overlay = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(FRAME_SIZE[1]):
            top_bias = int(30 * (1 - y / FRAME_SIZE[1]))
            bottom_bias = int(34 * max(0, (y - FRAME_SIZE[1] * 0.68) / (FRAME_SIZE[1] * 0.32)))
            alpha = max(top_bias, bottom_bias)
            if alpha:
                draw.line((0, y, FRAME_SIZE[0], y), fill=(23, 35, 31, alpha))
        if purpose in {"Hook", "Spiritual Value"}:
            draw.ellipse((-180, 180, 1260, 1220), fill=(255, 255, 255, 26))
        return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    def _product_box(self, purpose: str, attempt: int) -> tuple[int, int, int, int]:
        if purpose == "Hook":
            return (150, 360, 930, 1080)
        if purpose == "Product Features":
            return (95, 310, 985, 1130)
        if purpose == "Spiritual Value":
            return (135, 350, 945, 1110)
        if purpose == "Call To Action":
            return (105, 300, 975, 1110)
        if purpose == "Ending":
            return (160, 325, 920, 1050)
        return (120, 330, 960, 1100)

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
        subtitle_font = get_font(60 if len(scene.get("subtitle", "")) <= 12 else 50)
        small_font = get_font(28)
        product_x = product_box[0] + ((product_box[2] - product_box[0]) - product_img.width) // 2
        product_y = product_box[1] + ((product_box[3] - product_box[1]) - product_img.height) // 2
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle((product_x - 42, product_y - 42, product_x + product_img.width + 42, product_y + product_img.height + 42), radius=48, fill=(0, 0, 0, 58))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB"))
        draw.rounded_rectangle(
            (product_x - 28, product_y - 28, product_x + product_img.width + 28, product_y + product_img.height + 28),
            radius=34,
            fill="#ffffff",
            outline="#d6c4a8",
            width=3,
        )
        canvas.paste(product_img, (product_x, product_y))
        draw.rounded_rectangle((64, 76, 1016, 230), radius=24, fill="#fffaf2", outline="#dcc7a6", width=2)
        draw.text((92, 100), product.get("name", "Temple Product"), fill="#17231f", font=title_font)
        draw.text((96, 168), storyboard_scene.get("shotType", scene.get("purpose", "")), fill="#6f5a3f", font=scene_font)
        safe_box = (72, 1402, 1008, 1736)
        draw.rounded_rectangle(safe_box, radius=28, fill="#111f1b")
        draw.rounded_rectangle((safe_box[0] + 10, safe_box[1] + 10, safe_box[2] - 10, safe_box[3] - 10), radius=22, outline="#e0bd76", width=2)
        lines = wrap_text(draw, scene.get("subtitle", ""), subtitle_font, 860)
        y = safe_box[1] + 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=subtitle_font)
            draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=subtitle_font)
            y += 76
        draw.rounded_rectangle((720, 1780, 1022, 1848), radius=14, fill="#1f5c4d")
        draw.text((750, 1797), "Temple AI Studio", fill="#ffffff", font=small_font)


class ImagePipeline:
    def __init__(self, provider: str = DEFAULT_PROVIDER, max_retries: int = MAX_RETRIES):
        self.provider_name = provider
        self.max_retries = max_retries
        self.provider = LocalCommercialCompositeProvider()

    def run(self, project: dict[str, Any], product: dict[str, Any], project_dir: Path, emma_root: Path | None = None) -> dict[str, Any]:
        asset_manager = AssetManager(Path(project_dir), project["id"])
        emma_core = EmmaCore(emma_root)
        emma_status = emma_core.initialize()
        project_uses_emma = project_requires_emma(project)
        emma_catalog = available_fingerprint_paths(emma_core.write_identity_fingerprint())
        emma_videos = available_emma_video_paths(Path(emma_root)) if emma_root else []
        used_emma_videos: set[str] = set()
        product_assets = asset_manager.register_product_assets(product)
        product_source_images = [
            Path(item["path"])
            for item in product_assets
            if Path(item["path"]).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
            and Path(item["path"]).exists()
        ]
        has_product_references = bool(product_source_images)
        source_images = list(product_source_images)
        if not source_images and project.get("mode") == "text-only" and project_uses_emma and emma_catalog:
            source_images = list(emma_catalog)
        if not source_images and project.get("mode") == "text-only":
            source = asset_manager.reference_root / "text-only-source.png"
            self._create_text_only_source(source, project, product)
            asset_manager.register(
                source,
                asset_type="generated-reference",
                role="text-only-visual-source",
                provider=self.provider.name,
                source="traditional-chinese-request",
                metadata={"mode": "text-only"},
            )
            source_images = [source]
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
            default_source = source_images[index % len(source_images)]
            if (
                project_uses_emma
                and not has_product_references
                and scene.get("purpose") == "Product Features"
            ):
                product_hold_anchor = (
                    Path(emma_root)
                    / "emma"
                    / "intake"
                    / "synthetic-seed-v1"
                    / "01_identity_anchors"
                    / "emma_anchor_03_product_hold_white_tee.png"
                )
                if product_hold_anchor.is_file():
                    default_source = product_hold_anchor.resolve()
            seed = self._stable_seed(project["id"], scene["id"], scene.get("version", 1))
            prompt_bundle = prompt_by_scene[scene["id"]]["openai"]
            story_scene = story_by_scene[scene["id"]]
            presenter_purposes = {"Hook", "Spiritual Value", "Call To Action", "Ending"}
            require_emma = (
                project_uses_emma and scene.get("purpose") in presenter_purposes
            ) or scene_requires_emma(scene)
            emma_references = emma_core.select_references("openai", generation_type="image", require_emma=require_emma)
            if require_emma and emma_references["overall"] == "BLOCKED":
                raise RuntimeError(f"Emma references are required but unavailable for scene: {scene['id']}")
            emma_sources = merge_unique_paths(
                available_reference_paths(emma_references),
                emma_catalog,
            ) if require_emma else []
            if require_emma and not emma_sources:
                raise RuntimeError(f"Emma references are registered but their files are unavailable for scene: {scene['id']}")
            best_record = None
            best_quality = None
            best_emma = None
            for attempt in range(self.max_retries + 1):
                source = emma_sources[(index + attempt) % len(emma_sources)] if emma_sources else default_source
                source_role = "emma-identity-reference" if emma_sources else "product-reference"
                output = asset_manager.generated_root / f"{scene['order']:02d}-{scene['id']}-v{scene.get('version', 1)}-a{attempt}.png"
                generation = self.provider.generate(scene, story_scene, prompt_bundle, product, source, output, seed, attempt)
                generation["sourceImage"] = str(source)
                generation["sourceRole"] = source_role
                generation["sourceSha256"] = sha256_file(source)
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
                        "sourceRole": source_role,
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
            scene["visualProvenance"] = {
                "provider": best_record.get("provider") if best_record else "",
                "model": best_record.get("model") if best_record else "",
                "sourceImage": best_record.get("sourceImage") if best_record else "",
                "sourceRole": best_record.get("sourceRole") if best_record else "",
                "sourceSha256": best_record.get("sourceSha256") if best_record else "",
            }
            if (
                project_uses_emma
                and not has_product_references
                and scene.get("purpose") == "Introduction"
            ):
                product_hold_anchor = (
                    Path(emma_root)
                    / "emma"
                    / "intake"
                    / "synthetic-seed-v1"
                    / "01_identity_anchors"
                    / "emma_anchor_03_product_hold_white_tee.png"
                )
                if product_hold_anchor.is_file():
                    hero_path = asset_manager.generated_root / (
                        f"{scene['order']:02d}-{scene['id']}-product-hero-v{scene.get('version', 1)}.png"
                    )
                    self._create_product_hero_still(product_hold_anchor, hero_path)
                    scene["videoStillPath"] = str(hero_path)
                    scene["visualProvenance"].update(
                        {
                            "sourceImage": str(product_hold_anchor.resolve()),
                            "sourceRole": "emma-product-hold-anchor",
                            "sourceSha256": sha256_file(product_hold_anchor),
                            "videoStill": str(hero_path),
                            "videoStillRole": "product-hero-crop",
                        }
                    )
            if project_uses_emma and scene.get("purpose") == "Product Features" and best_record:
                detail_path = asset_manager.generated_root / (
                    f"{scene['order']:02d}-{scene['id']}-product-detail-v{scene.get('version', 1)}.png"
                )
                self._create_product_detail_still(
                    Path(best_record["sourceImage"]),
                    detail_path,
                )
                scene["videoStillPath"] = str(detail_path)
                scene["visualProvenance"]["videoStill"] = str(detail_path)
                scene["visualProvenance"]["videoStillRole"] = "product-detail-crop"
            if project_uses_emma and scene.get("purpose") == "Hook":
                scene["preferLocalVideoGeneration"] = True
            elif (
                project_uses_emma
                and scene.get("purpose") != "Product Features"
                and not scene.get("videoStillPath")
                and not (
                    has_product_references
                    and scene.get("purpose") == "Introduction"
                )
                and emma_videos
            ):
                source_video = select_emma_video_for_scene(
                    emma_videos,
                    str(scene.get("purpose", "")),
                    used_emma_videos,
                )
                if source_video:
                    scene["sourceVideoPath"] = str(source_video)
                    scene["sourceVideoRole"] = "approved-emma-source-video"
                    used_emma_videos.add(str(source_video.resolve()).lower())
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

    def _create_text_only_source(self, path: Path, project: dict[str, Any], product: dict[str, Any]) -> None:
        canvas = Image.new("RGB", FRAME_SIZE, "#eef3ef")
        draw = ImageDraw.Draw(canvas)
        title_font = get_font(70)
        body_font = get_font(46)
        small_font = get_font(30)
        draw.rectangle((0, 0, FRAME_SIZE[0], 520), fill="#17231f")
        draw.rectangle((0, 520, FRAME_SIZE[0], FRAME_SIZE[1]), fill="#f7f3ec")
        draw.rounded_rectangle((86, 650, 994, 1450), radius=40, fill="#ffffff", outline="#d6c4a8", width=4)
        draw.text((86, 126), "Temple AI Studio", fill="#e6c98b", font=small_font)
        title = product.get("name") or "純文字影片"
        draw.text((86, 210), title, fill="#ffffff", font=title_font)
        text = project.get("requirement") or product.get("description") or "神殿內容"
        y = 760
        for line in wrap_text(draw, text, body_font, 790):
            draw.text((140, y), line, fill="#25372f", font=body_font)
            y += 92
        draw.rounded_rectangle((140, 1280, 940, 1370), radius=18, fill="#245c4f")
        draw.text((230, 1304), "繁體中文內容視覺來源", fill="#ffffff", font=small_font)
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path, optimize=True)

    def _create_product_detail_still(self, source_path: Path, output_path: Path) -> None:
        with Image.open(source_path) as raw:
            source = raw.convert("RGB")
            if "emma_anchor_03_product_hold" in source_path.stem.lower():
                source = source.crop(
                    (
                        int(source.width * 0.46),
                        int(source.height * 0.34),
                        int(source.width * 0.72),
                        int(source.height * 0.56),
                    )
                )
            detail = fit_cover(source, FRAME_SIZE)
            detail = ImageEnhance.Contrast(detail).enhance(1.04)
            detail = ImageEnhance.Sharpness(detail).enhance(1.18)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        detail.save(output_path, optimize=True, quality=96)

    def _create_product_hero_still(self, source_path: Path, output_path: Path) -> None:
        with Image.open(source_path) as raw:
            source = raw.convert("RGB")
            source = source.crop(
                (
                    int(source.width * 0.18),
                    int(source.height * 0.18),
                    int(source.width * 0.82),
                    int(source.height * 0.90),
                )
            )
            hero = fit_cover(source, FRAME_SIZE)
            hero = ImageEnhance.Contrast(hero).enhance(1.03)
            hero = ImageEnhance.Sharpness(hero).enhance(1.10)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hero.save(output_path, optimize=True, quality=96)

    def _stable_seed(self, *parts: Any) -> int:
        value = "|".join(str(part) for part in parts)
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % 2_147_483_647


def scene_requires_emma(scene: dict[str, Any]) -> bool:
    content = " ".join(
        str(scene.get(key, "")) for key in ["narration", "subtitle", "prompt", "visualDescription"]
    ).lower()
    return "emma" in content or "艾瑪" in content


def project_requires_emma(project: dict[str, Any]) -> bool:
    content = " ".join(
        str(project.get(key, ""))
        for key in ["requirement", "title", "description"]
    ).lower()
    return "emma" in content or "艾瑪" in content


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def available_reference_paths(selection: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for reference in selection.get("references", []):
        source_path = Path(str(reference.get("sourcePath", "")))
        stored_path = Path(str(reference.get("path", "")))
        path = source_path if source_path.exists() else stored_path
        key = str(path.resolve()).lower() if path.exists() else ""
        if key and key not in seen:
            seen.add(key)
            paths.append(path)
    return paths


def available_fingerprint_paths(fingerprint: dict[str, Any]) -> list[Path]:
    return merge_unique_paths(
        [
            (
                Path(str(reference.get("sourcePath", "")))
                if Path(str(reference.get("sourcePath", ""))).exists()
                else Path(str(reference.get("path", "")))
            )
            for reference in fingerprint.get("references", [])
            if Path(str(reference.get("sourcePath", ""))).exists()
            or Path(str(reference.get("path", ""))).exists()
        ]
    )


def merge_unique_paths(*groups: list[Path]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for group in groups:
        for path in group:
            resolved = Path(path).resolve()
            key = str(resolved).lower()
            if key not in seen and resolved.is_file():
                seen.add(key)
                paths.append(resolved)
    return paths


def available_emma_video_paths(emma_root: Path) -> list[Path]:
    video_root = Path(emma_root) / "emma" / "intake" / "video"
    if not video_root.is_dir():
        return []
    return sorted(
        path.resolve()
        for path in video_root.iterdir()
        if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
    )


def select_emma_video_for_scene(
    videos: list[Path],
    purpose: str,
    used: set[str],
) -> Path | None:
    if not videos:
        return None
    preferred_slots = {
        "Introduction": 4,
        "Spiritual Value": 1,
        "Call To Action": 2,
        "Ending": 3,
    }
    preferred = preferred_slots.get(purpose)
    candidates: list[Path] = []
    if preferred is not None and preferred < len(videos):
        candidates.append(videos[preferred])
    candidates.extend(videos)
    for candidate in candidates:
        if str(candidate.resolve()).lower() not in used:
            return candidate
    return None


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
