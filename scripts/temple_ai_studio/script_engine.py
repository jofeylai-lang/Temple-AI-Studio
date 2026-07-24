from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_ENGINE_VERSION = "1.0.0"
DEFAULT_PLATFORM = "Instagram Reels"
DEFAULT_DURATION = 30
SCENE_ARC = [
    ("hook", "Hook", 0.12),
    ("introduction", "Introduction", 0.17),
    ("product-features", "Product Features", 0.24),
    ("spiritual-value", "Spiritual Value", 0.20),
    ("call-to-action", "Call To Action", 0.15),
    ("ending", "Ending", 0.12),
]
PLATFORM_PROFILES = {
    "instagram": {
        "display": "Instagram Reels",
        "captionLimit": 2200,
        "subtitleMaxChars": 18,
        "style": "溫柔、精緻、適合手機直式觀看",
    },
    "tiktok": {
        "display": "TikTok",
        "captionLimit": 2200,
        "subtitleMaxChars": 16,
        "style": "節奏更快、開頭更直接、字幕更短",
    },
    "youtube": {
        "display": "YouTube Shorts",
        "captionLimit": 5000,
        "subtitleMaxChars": 20,
        "style": "資訊清楚、商品價值完整、收尾明確",
    },
}
OBJECTIVE_KEYWORDS = {
    "銷售轉換": ["購買", "下單", "預約", "私訊", "促銷", "優惠", "導購", "成交"],
    "品牌信任": ["品牌", "故事", "信任", "介紹", "理念", "由來"],
    "新品曝光": ["新品", "上市", "新款", "推出", "首發"],
    "教育說明": ["教學", "用法", "怎麼用", "步驟", "說明", "介紹功效"],
    "情感共鳴": ["療癒", "放鬆", "安心", "祝福", "陪伴", "情緒", "能量"],
}
AUDIENCE_KEYWORDS = {
    "日常靜心與空間儀式使用者": ["靜心", "放鬆", "空間", "香氛", "居家", "療癒"],
    "正在尋找祝福禮物的顧客": ["禮物", "送禮", "祝福", "生日", "開幕", "紀念"],
    "對身心靈商品有興趣的顧客": ["神聖", "能量", "儀式", "水晶", "塔羅", "冥想"],
    "第一次認識品牌的新客": ["第一次", "新客", "入門", "不知道", "了解"],
}
CLAIM_RISK_TERMS = [
    "保證",
    "治療",
    "治癒",
    "醫療",
    "一定有效",
    "立即見效",
    "改命",
    "百分之百",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or fallback


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def split_durations(total: int) -> list[int]:
    values = [max(2, round(total * weight)) for _, _, weight in SCENE_ARC]
    values[-1] += total - sum(values)
    return values


def unique_list(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        value = clean_text(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def select_platform(raw_platform: str | None) -> dict[str, str]:
    text = clean_text(raw_platform, DEFAULT_PLATFORM).lower()
    if "tiktok" in text or "抖音" in text:
        return PLATFORM_PROFILES["tiktok"]
    if "youtube" in text or "short" in text:
        return PLATFORM_PROFILES["youtube"]
    return PLATFORM_PROFILES["instagram"]


def detect_by_keywords(text: str, mapping: dict[str, list[str]], fallback: str) -> str:
    for label, keywords in mapping.items():
        if any(keyword in text for keyword in keywords):
            return label
    return fallback


def infer_product_type(product: dict[str, Any], request: str) -> str:
    source = f"{product.get('name', '')} {product.get('category', '')} {product.get('description', '')} {request}"
    if any(word in source for word in ["蠟燭", "香氛", "香氣", "燭"]):
        return "香氛儀式商品"
    if any(word in source for word in ["水晶", "礦石", "晶石"]):
        return "水晶能量商品"
    if any(word in source for word in ["課程", "諮詢", "服務", "占卜", "塔羅"]):
        return "身心靈服務"
    if any(word in source for word in ["飾品", "手鍊", "項鍊"]):
        return "祝福飾品"
    return clean_text(product.get("category"), "Temple 商品")


def analyze_intent(product: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    request = clean_text(payload.get("requirement"), "請製作一支溫柔、清楚、適合社群短影音的商品介紹影片。")
    product_text = " ".join(
        clean_text(product.get(key)) for key in ["name", "category", "description", "sellingPoint", "spiritualInfo", "targetAudience"]
    )
    combined = f"{request} {product_text}"
    platform = select_platform(payload.get("platform"))
    target_audience = clean_text(payload.get("targetAudience") or product.get("targetAudience"))
    if not target_audience:
        target_audience = detect_by_keywords(combined, AUDIENCE_KEYWORDS, "對身心靈商品有興趣、正在尋找日常安定感的顧客")
    objective = detect_by_keywords(combined, OBJECTIVE_KEYWORDS, "情感共鳴")
    product_type = infer_product_type(product, request)
    tone = "溫柔、可信、安定、帶有儀式感"
    if objective == "銷售轉換":
        tone = "溫柔但明確，引導觀眾採取下一步"
    elif objective == "教育說明":
        tone = "清楚、親切、容易理解"
    return {
        "request": request,
        "platform": platform,
        "targetAudience": target_audience,
        "marketingObjective": objective,
        "productType": product_type,
        "tone": tone,
        "language": "zh-TW",
    }


def product_value(product: dict[str, Any], key: str, fallback: str) -> str:
    return clean_text(product.get(key), fallback)


def sentence_limit(text: str, max_chars: int) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip("，。、 ") + "…"


def build_scene_templates(product: dict[str, Any], intent: dict[str, Any]) -> list[dict[str, str]]:
    name = product_value(product, "name", "Temple 精選商品")
    category = product_value(product, "category", intent["productType"])
    description = product_value(product, "description", "為日常生活帶來安定感與儀式感。")
    selling_point = product_value(product, "sellingPoint", "細緻設計、適合日常使用，也適合作為一份有心意的禮物。")
    spiritual = product_value(product, "spiritualInfo", "提醒自己放慢腳步，把注意力帶回內在與當下。")
    audience = intent["targetAudience"]
    return [
        {
            "purpose": "Hook",
            "visual": f"以安靜、有呼吸感的畫面開場，呈現{audience}在日常中渴望被安定與照顧的情境。",
            "narration": f"有時候，我們需要的不是更多忙碌，而是一個讓心慢下來的片刻。",
            "subtitle": "給自己一個安定片刻",
            "promptGoal": "quiet emotional opening, soft natural light, vertical short video framing, calm premium Temple atmosphere",
        },
        {
            "purpose": "Introduction",
            "visual": f"清楚展示{name}，畫面乾淨，商品要成為第一視覺焦點。",
            "narration": f"這是{name}，一款為{category}而設計的 Temple 商品。",
            "subtitle": f"{name}｜{category}",
            "promptGoal": "clear product hero shot, premium product photography, gentle camera push in, no clutter",
        },
        {
            "purpose": "Product Features",
            "visual": f"用近景展示商品細節、材質、包裝或使用情境，讓觀眾理解它的具體特色。",
            "narration": f"{selling_point}",
            "subtitle": "看得見的細節與心意",
            "promptGoal": "macro detail shots, visible product texture, elegant hands or tabletop setup, commercial quality",
        },
        {
            "purpose": "Spiritual Value",
            "visual": f"呈現商品被使用時的氛圍，不做誇大承諾，重點放在感受、祝福與日常儀式。",
            "narration": f"{spiritual}",
            "subtitle": "把祝福放進日常",
            "promptGoal": "ritual mood, warm atmosphere, calm movement, respectful spiritual product presentation",
        },
        {
            "purpose": "Call To Action",
            "visual": f"再次展示{name}與可購買、私訊或預約的下一步提示。",
            "narration": f"如果你也想為生活準備一份安定的提醒，歡迎把{name}帶回你的日常。",
            "subtitle": "歡迎私訊了解",
            "promptGoal": "final product offer shot, clean CTA composition, readable space for subtitle, social commerce ready",
        },
        {
            "purpose": "Ending",
            "visual": f"品牌收尾，保留商品、Logo 或品牌名稱，畫面安靜結束。",
            "narration": f"Temple，陪你把每一天過得更有光。",
            "subtitle": "Temple 陪你安定日常",
            "promptGoal": "brand ending frame, premium calm closing shot, product and Temple brand presence",
        },
    ]


def build_prompt(scene: dict[str, str], product: dict[str, Any], intent: dict[str, Any], platform: dict[str, str]) -> str:
    name = product_value(product, "name", "Temple product")
    material_count = len(product.get("materials", []) or [])
    source_note = "use uploaded product photos as identity and product reference" if material_count else "block visual generation until product photos are provided"
    return (
        f"Temple product video scene. Product: {name}. Scene purpose: {scene['purpose']}. "
        f"Visual goal: {scene['visual']} Motion: subtle cinematic movement, stable product framing, vertical 9:16. "
        f"Style: {platform['style']}. Tone: {intent['tone']}. Source fidelity: {source_note}. "
        f"Avoid exaggerated medical, spiritual, or guaranteed-result claims. Commercial quality, clean lighting, readable composition."
    )


def generate_video_script_package(product: dict[str, Any], payload: dict[str, Any], project_id: str | None = None) -> dict[str, Any]:
    project_id = project_id or new_id("script-project")
    intent = analyze_intent(product, payload)
    platform = intent["platform"]
    total_duration = clamp(int(payload.get("duration") or DEFAULT_DURATION), 18, 60)
    durations = split_durations(total_duration)
    templates = build_scene_templates(product, intent)
    scenes = []
    prompts = []
    cursor = 0.0
    subtitle_limit = int(platform["subtitleMaxChars"])
    category = product_value(product, "category", intent["productType"])
    for index, template in enumerate(templates):
        duration = durations[index]
        start = cursor
        end = cursor + duration
        cursor = end
        scene_id = f"scene-{index + 1:02d}-{SCENE_ARC[index][0]}"
        subtitle = sentence_limit(template["subtitle"], subtitle_limit)
        if not contains_traditional_chinese(subtitle):
            subtitle = sentence_limit(f"{category}｜{template['subtitle']}", subtitle_limit)
        prompt = build_prompt(template, product, intent, platform)
        scene = {
            "id": scene_id,
            "order": index + 1,
            "purpose": template["purpose"],
            "duration": duration,
            "start": round(start, 2),
            "end": round(end, 2),
            "visualDescription": template["visual"],
            "narration": template["narration"],
            "subtitle": subtitle,
            "prompt": prompt,
            "music": "溫柔環境音、冥想質感、低干擾節奏，避免蓋過旁白。",
            "transition": "柔和淡入淡出或乾淨剪接，保持手機短影音節奏。",
            "optionalEffects": ["輕微推鏡", "柔光", "細緻陰影", "字幕安全區"],
            "status": "Ready for Preview",
            "approved": False,
            "version": 1,
            "updatedAt": now_iso(),
        }
        scenes.append(scene)
        prompts.append(
            {
                "id": new_id("prompt"),
                "sceneId": scene_id,
                "category": "video",
                "providerMode": "local-rule-script",
                "text": prompt,
                "createdAt": now_iso(),
            }
        )
    script = "\n".join(scene["narration"] for scene in scenes)
    name = product_value(product, "name", "Temple 精選商品")
    category = product_value(product, "category", intent["productType"])
    caption = build_caption(name, category, intent, platform)
    metadata = {
        "schema": "temple-ai-studio.script-package.v1",
        "scriptEngineVersion": SCRIPT_ENGINE_VERSION,
        "projectId": project_id,
        "productName": name,
        "productCategory": category,
        "productType": intent["productType"],
        "targetAudience": intent["targetAudience"],
        "marketingObjective": intent["marketingObjective"],
        "tone": intent["tone"],
        "platform": platform["display"],
        "language": "zh-TW",
        "duration": total_duration,
        "sceneCount": len(scenes),
        "providerMode": "local-rule-template",
        "createdAt": now_iso(),
        "sourceMaterials": [item.get("fileName", "") for item in product.get("materials", []) or []],
    }
    package = {
        "requirement": intent["request"],
        "platform": platform["display"],
        "targetAudience": intent["targetAudience"],
        "duration": total_duration,
        "script": script,
        "scenes": scenes,
        "prompts": prompts,
        "caption": caption,
        "tags": unique_list(["Temple", category, "身心靈", "儀式感", platform["display"], intent["marketingObjective"]]),
        "seoKeywords": unique_list([name, category, "Temple", "儀式感", "祝福禮物", "靜心"]),
        "thumbnailSuggestion": f"以{name}清楚入鏡，搭配短字標題「給自己一個安定片刻」，保留品牌名稱 Temple。",
        "metadata": metadata,
        "quality": validate_script_package(scenes, script, caption),
    }
    return package


def build_caption(name: str, category: str, intent: dict[str, Any], platform: dict[str, str]) -> str:
    caption = (
        f"{name}｜把一份安定感放進日常。\n\n"
        f"適合想要{intent['targetAudience']}的你，也適合作為一份帶著心意的祝福。\n\n"
        "不需要把生活變得很複雜，只要留一個片刻，讓自己慢慢回到內在。\n\n"
        "歡迎私訊了解。"
    )
    if len(caption) > int(platform["captionLimit"]):
        caption = caption[: int(platform["captionLimit"]) - 1].rstrip() + "…"
    return caption


def contains_traditional_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def validate_script_package(scenes: list[dict[str, Any]], script: str, caption: str) -> dict[str, Any]:
    checks = []
    checks.append({"name": "scene-count", "ok": len(scenes) == len(SCENE_ARC), "expected": len(SCENE_ARC), "actual": len(scenes)})
    checks.append({"name": "script-not-empty", "ok": bool(clean_text(script)), "characters": len(script)})
    checks.append({"name": "caption-not-empty", "ok": bool(clean_text(caption)), "characters": len(caption)})
    for scene in scenes:
        checks.extend(
            [
                {"name": f"{scene['id']}:narration-zh-tw", "ok": contains_traditional_chinese(scene.get("narration", ""))},
                {"name": f"{scene['id']}:subtitle-zh-tw", "ok": contains_traditional_chinese(scene.get("subtitle", ""))},
                {"name": f"{scene['id']}:prompt-present", "ok": bool(clean_text(scene.get("prompt", "")))},
                {"name": f"{scene['id']}:duration-positive", "ok": int(scene.get("duration", 0)) > 0, "duration": scene.get("duration")},
            ]
        )
    risky_terms = [term for term in CLAIM_RISK_TERMS if term in script or term in caption]
    checks.append({"name": "no-high-risk-claims", "ok": not risky_terms, "riskyTerms": risky_terms})
    failed = [check for check in checks if not check.get("ok")]
    return {
        "schema": "temple-ai-studio.script-quality.v1",
        "createdAt": now_iso(),
        "overall": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failedChecks": failed,
    }


def self_test() -> dict[str, Any]:
    product = {
        "name": "Temple Energy Candle",
        "category": "香氛蠟燭",
        "description": "適合睡前、冥想與安定空間的手作香氛蠟燭。",
        "sellingPoint": "手工製作、氣味溫柔、包裝精緻，適合自用與送禮。",
        "spiritualInfo": "象徵祝福、淨化與陪伴，提醒使用者回到安定的內在節奏。",
        "targetAudience": "想在日常中建立靜心儀式感的顧客",
        "materials": [{"fileName": "demo-candle.png"}],
    }
    package = generate_video_script_package(product, {"requirement": "請做一支溫柔、有儀式感、能引導私訊購買的 IG Reels。"}, "self-test-project")
    return {
        "schema": "temple-ai-studio.script-engine-self-test.v1",
        "createdAt": now_iso(),
        "overall": package["quality"]["overall"],
        "sceneCount": len(package["scenes"]),
        "duration": package["duration"],
        "platform": package["platform"],
        "failedChecks": package["quality"]["failedChecks"],
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Script Engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--product-json", required=True)
    generate_parser.add_argument("--request", required=True)
    generate_parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    generate_parser.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    generate_parser.add_argument("--project-id", default="")
    generate_parser.add_argument("--output", required=True)

    self_test_parser = sub.add_parser("self-test")
    self_test_parser.add_argument("--output")

    args = parser.parse_args()
    if args.command == "generate":
        product = read_json(Path(args.product_json))
        payload = {"requirement": args.request, "platform": args.platform, "duration": args.duration}
        result = generate_video_script_package(product, payload, args.project_id or None)
        write_json(Path(args.output), result)
    elif args.command == "self-test":
        result = self_test()
        if args.output:
            write_json(Path(args.output), result)
    else:
        raise ValueError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("overall", result.get("quality", {}).get("overall", "FAIL")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
