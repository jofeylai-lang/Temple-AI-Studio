from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROMPT_TRANSLATION_SCHEMA = "temple-ai-studio.provider-prompts.v1"
PROMPT_TRANSLATION_ENGINE_VERSION = "1.0.0"
SUPPORTED_PROVIDERS = ["comfyui", "flux", "sdxl", "wan", "ltx", "kling", "runway", "openai", "future"]


PROVIDER_ADAPTERS = {
    "comfyui": {"style": "node workflow ready, explicit positive and negative prompt blocks", "motion": "image generation or image-to-video prep"},
    "flux": {"style": "natural language, high fidelity product photography, concise negatives", "motion": "still image generation"},
    "sdxl": {"style": "weighted photographic prompt, product detail, strong negative prompt", "motion": "still image generation"},
    "wan": {"style": "video-first cinematic scene description", "motion": "controlled commercial short-video movement"},
    "ltx": {"style": "image-to-video scene motion prompt, identity and product consistency", "motion": "subtle camera movement"},
    "kling": {"style": "commercial video prompt with motion and subject consistency", "motion": "short-form realistic movement"},
    "runway": {"style": "director-style video prompt, clean camera language", "motion": "social video movement"},
    "openai": {"style": "clear instruction prompt, product-safe, composition-focused", "motion": "image generation"},
    "future": {"style": "provider-neutral prompt contract", "motion": "capability dependent"},
}


NEGATIVE_BASE = [
    "low quality",
    "blurry",
    "warped product",
    "wrong logo",
    "unreadable text",
    "extra fingers",
    "distorted packaging",
    "medical claim",
    "guaranteed result",
    "overcrowded composition",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def build_positive_prompt(scene: dict[str, Any], storyboard: dict[str, Any], product: dict[str, Any], provider: str) -> str:
    adapter = PROVIDER_ADAPTERS[provider]
    product_name = clean(product.get("name")) or "Temple product"
    category = clean(product.get("category")) or "commercial product"
    return (
        f"Commercial vertical 9:16 Temple product scene for {provider}. "
        f"Product: {product_name}. Category: {category}. "
        f"Scene purpose: {scene.get('purpose')}. Shot type: {storyboard.get('shotType')}. "
        f"Camera movement: {storyboard.get('cameraMovement')}. Emotion: {storyboard.get('emotion')}. "
        f"Visual focus: {storyboard.get('visualFocus')}. Product focus: {storyboard.get('productFocus')}. "
        f"Lighting: {storyboard.get('lighting')}. Composition: {storyboard.get('composition')}. "
        f"Background: {storyboard.get('backgroundRequirements')}. "
        f"Subtitle safe area at the bottom. Premium commercial quality. "
        f"Preserve product appearance from reference photos. Provider style: {adapter['style']}."
    )


def build_negative_prompt(provider: str) -> str:
    extras = []
    if provider in ["sdxl", "comfyui"]:
        extras = ["bad anatomy", "jpeg artifacts", "duplicate product", "fake brand text"]
    if provider in ["wan", "ltx", "kling", "runway"]:
        extras = ["camera shake", "identity drift", "object morphing", "talking without narration cue"]
    return ", ".join(NEGATIVE_BASE + extras)


def translate_prompts(script_package: dict[str, Any], storyboard: dict[str, Any], product: dict[str, Any], providers: list[str] | None = None) -> dict[str, Any]:
    providers = [item.lower() for item in (providers or SUPPORTED_PROVIDERS)]
    providers = [item for item in providers if item in SUPPORTED_PROVIDERS]
    storyboard_by_id = {scene["id"]: scene for scene in storyboard.get("scenes", [])}
    scenes = []
    for scene in script_package.get("scenes", []) or []:
        story_scene = storyboard_by_id.get(scene["id"], {})
        provider_prompts = {}
        for provider in providers:
            provider_prompts[provider] = {
                "provider": provider,
                "positive": build_positive_prompt(scene, story_scene, product, provider),
                "negative": build_negative_prompt(provider),
                "seedPolicy": "stable per scene version unless retry is required",
                "adapterVersion": PROMPT_TRANSLATION_ENGINE_VERSION,
            }
        scenes.append(
            {
                "sceneId": scene["id"],
                "order": scene["order"],
                "purpose": scene["purpose"],
                "providers": provider_prompts,
            }
        )
    return {
        "schema": PROMPT_TRANSLATION_SCHEMA,
        "version": PROMPT_TRANSLATION_ENGINE_VERSION,
        "createdAt": now_iso(),
        "projectId": script_package.get("metadata", {}).get("projectId", ""),
        "providers": providers,
        "scenes": scenes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Prompt Translation Engine.")
    parser.add_argument("--script-package", required=True)
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--providers", default=",".join(SUPPORTED_PROVIDERS))
    args = parser.parse_args()
    package = json.loads(Path(args.script_package).read_text(encoding="utf-8-sig"))
    storyboard = json.loads(Path(args.storyboard).read_text(encoding="utf-8-sig"))
    product = json.loads(Path(args.product_json).read_text(encoding="utf-8-sig"))
    result = translate_prompts(package, storyboard, product, [item.strip() for item in args.providers.split(",")])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
