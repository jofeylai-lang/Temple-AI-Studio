from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


STORYBOARD_SCHEMA = "temple-ai-studio.storyboard.v1"
STORYBOARD_ENGINE_VERSION = "1.0.0"


SCENE_DIRECTIONS = {
    "Hook": {
        "shotType": "emotional establishing close-up",
        "cameraMovement": "slow push-in",
        "emotion": "calm curiosity",
        "visualFocus": "viewer need and atmosphere",
        "productFocus": "soft presence, not yet hard-selling",
        "emmaBehavior": "not required unless Emma is explicitly part of the request",
        "backgroundRequirements": "quiet premium background with negative space",
        "lighting": "soft natural or warm ritual light",
        "composition": "center-safe subject, clean bottom subtitle area",
    },
    "Introduction": {
        "shotType": "product hero shot",
        "cameraMovement": "gentle reveal",
        "emotion": "trust",
        "visualFocus": "clear product identity",
        "productFocus": "main product must be recognizable",
        "emmaBehavior": "optional hand presentation only when reference material exists",
        "backgroundRequirements": "uncluttered surface or brand environment",
        "lighting": "clean softbox feel",
        "composition": "product centered, enough margin for mobile crop",
    },
    "Product Features": {
        "shotType": "detail montage frame",
        "cameraMovement": "slow lateral drift",
        "emotion": "interest",
        "visualFocus": "texture, material, package, usage detail",
        "productFocus": "product detail must stay sharp",
        "emmaBehavior": "optional natural hand interaction",
        "backgroundRequirements": "supporting props allowed but product remains dominant",
        "lighting": "directional soft light showing texture",
        "composition": "rule of thirds with product detail foreground",
    },
    "Spiritual Value": {
        "shotType": "ritual mood shot",
        "cameraMovement": "slow breathing motion",
        "emotion": "comfort",
        "visualFocus": "feeling, blessing, daily ritual",
        "productFocus": "visible within ritual context",
        "emmaBehavior": "optional quiet presence, no identity invention",
        "backgroundRequirements": "warm, respectful, no exaggerated mystical claims",
        "lighting": "warm glow with controlled contrast",
        "composition": "product plus environmental context",
    },
    "Call To Action": {
        "shotType": "commerce-ready product shot",
        "cameraMovement": "stable hold",
        "emotion": "gentle confidence",
        "visualFocus": "next action",
        "productFocus": "product name and appearance clear",
        "emmaBehavior": "optional smile or hand gesture only with approved references",
        "backgroundRequirements": "clean layout with subtitle/CTA safety area",
        "lighting": "bright and trustworthy",
        "composition": "product dominant, clear CTA zone",
    },
    "Ending": {
        "shotType": "brand closing frame",
        "cameraMovement": "soft fade out",
        "emotion": "closure",
        "visualFocus": "brand memory",
        "productFocus": "product and Temple name visible",
        "emmaBehavior": "not required",
        "backgroundRequirements": "minimal brand-friendly background",
        "lighting": "warm final glow",
        "composition": "balanced product and brand lockup",
    },
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def build_storyboard(script_package: dict[str, Any], product: dict[str, Any] | None = None) -> dict[str, Any]:
    scenes = []
    for scene in script_package.get("scenes", []) or []:
        direction = SCENE_DIRECTIONS.get(scene.get("purpose"), SCENE_DIRECTIONS["Product Features"])
        scenes.append(
            {
                "id": scene["id"],
                "order": scene["order"],
                "purpose": scene["purpose"],
                "duration": scene["duration"],
                "shotType": direction["shotType"],
                "cameraMovement": direction["cameraMovement"],
                "transition": scene.get("transition") or "clean cut",
                "emotion": direction["emotion"],
                "visualFocus": direction["visualFocus"],
                "productFocus": direction["productFocus"],
                "emmaBehavior": direction["emmaBehavior"],
                "backgroundRequirements": direction["backgroundRequirements"],
                "lighting": direction["lighting"],
                "composition": direction["composition"],
                "sourceNarration": scene.get("narration", ""),
                "sourceSubtitle": scene.get("subtitle", ""),
                "sourcePrompt": scene.get("prompt", ""),
            }
        )
    failed = [item["id"] for item in scenes if not item.get("shotType") or not item.get("composition")]
    return {
        "schema": STORYBOARD_SCHEMA,
        "version": STORYBOARD_ENGINE_VERSION,
        "createdAt": now_iso(),
        "projectId": script_package.get("metadata", {}).get("projectId", ""),
        "productName": (product or {}).get("name") or script_package.get("metadata", {}).get("productName", ""),
        "platform": script_package.get("platform") or script_package.get("metadata", {}).get("platform", ""),
        "scenes": scenes,
        "quality": {"overall": "PASS" if not failed else "FAIL", "failedScenes": failed},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Storyboard Engine.")
    parser.add_argument("--script-package", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    package = json.loads(Path(args.script_package).read_text(encoding="utf-8-sig"))
    result = build_storyboard(package)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["quality"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
