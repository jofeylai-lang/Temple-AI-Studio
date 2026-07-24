from __future__ import annotations

import argparse
import json
import shutil
import statistics
import time
import tracemalloc
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.quality_check import detect_ffmpeg, evaluate_export
from temple_ai_studio.script_engine import generate_video_script_package
from temple_ai_studio.video_intelligence import run_video_generation_pipeline


VALIDATION_VERSION = "1.0.0"
VALIDATION_SCHEMA = "temple-ai-studio.product-validation.v1"
DEFAULT_CASE_COUNT = 100
REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = REPO_ROOT / "evaluations" / "quality-reviews" / "production-validation"
ARTIFACT_ROOT = REPO_ROOT.parent / "Temple AI Studio Validation Work"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_mean(values: list[float]) -> float:
    return round(statistics.mean(values), 4) if values else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return round(ordered[index], 4)


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\mingliu.ttc", r"C:\Windows\Fonts\arial.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    name: str
    product_name: str
    category: str
    requirement: str
    platform: str
    duration: int
    image_count: int
    asset_mode: str
    writing_style: str
    expected: str
    severity_if_fail: str


PRODUCTS = [
    ("temple-candle", "淨心能量蠟燭", "香氛蠟燭"),
    ("blessing-bracelet", "靜願黑曜石手鍊", "能量手鍊"),
    ("fortune-card", "每日祝福小卡", "療癒卡牌"),
    ("ritual-oil", "平安儀式精油", "芳香精油"),
    ("desk-altar", "迷你靜心供台", "居家擺飾"),
    ("singing-bowl", "銅製靜心音缽", "聲音療癒"),
    ("incense-set", "晨光線香組", "線香"),
    ("crystal-set", "七日水晶組", "水晶"),
]

STYLES = ["溫柔療癒", "高級商業", "節奏快速", "故事敘事", "節慶促銷", "新手友善", "品牌形象", "短影音爆款"]
PLATFORMS = ["Instagram Reels", "TikTok", "YouTube Shorts"]
EDGE_MODES = ["valid", "long_subtitle", "multilingual", "missing_assets", "invalid_assets", "empty_assets"]


def build_cases(count: int = DEFAULT_CASE_COUNT) -> list[ValidationCase]:
    cases: list[ValidationCase] = []
    for index in range(count):
        product_slug, product_name, category = PRODUCTS[index % len(PRODUCTS)]
        style = STYLES[(index // len(PRODUCTS)) % len(STYLES)]
        platform = PLATFORMS[index % len(PLATFORMS)]
        if index < int(count * 0.72):
            mode = "valid"
        elif index < int(count * 0.80):
            mode = "long_subtitle"
        elif index < int(count * 0.87):
            mode = "multilingual"
        elif index < int(count * 0.92):
            mode = "missing_assets"
        elif index < int(count * 0.97):
            mode = "invalid_assets"
        else:
            mode = "empty_assets"
        duration = 18 + (index % 4) * 6
        requirement = build_requirement(product_name, category, style, mode, index)
        expected = "handled_input_failure" if mode in {"missing_assets", "invalid_assets", "empty_assets"} else "production_export"
        cases.append(
            ValidationCase(
                case_id=f"PV-{index + 1:03d}-{product_slug}-{mode}",
                name=f"{product_name} {style} {platform}",
                product_name=product_name,
                category=category,
                requirement=requirement,
                platform=platform,
                duration=duration,
                image_count=1 + (index % 4),
                asset_mode=mode,
                writing_style=style,
                expected=expected,
                severity_if_fail="critical" if expected == "production_export" else "major",
            )
        )
    return cases


def build_requirement(product_name: str, category: str, style: str, mode: str, index: int) -> str:
    base = f"請用{style}風格，為{product_name}製作一支適合社群短影音的商品影片，強調質感、日常使用情境與安心感。"
    if mode == "long_subtitle":
        return base + "字幕可以稍長，但仍要清楚好讀，請避免誇大療效，並把重點放在商品能陪伴使用者整理心情。"
    if mode == "multilingual":
        return base + "內容以繁體中文為主，可以自然加入少量英文關鍵字，例如 calm、ritual、daily blessing。"
    if mode == "missing_assets":
        return f"測試缺少素材時的恢復流程：為{category}{product_name}建立影片，但素材檔案不存在。"
    if mode == "invalid_assets":
        return f"測試無效圖片時的恢復流程：為{product_name}建立影片，但上傳檔案不是有效圖片。"
    if mode == "empty_assets":
        return f"測試未上傳圖片時的提醒流程：為{product_name}建立影片。"
    return base + f"這是第 {index + 1} 個生產驗證案例。"


def create_product_assets(case: ValidationCase, root: Path) -> list[dict[str, Any]]:
    asset_dir = root / "source-assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    if case.asset_mode == "empty_assets":
        return []
    if case.asset_mode == "missing_assets":
        missing = asset_dir / f"{case.case_id}-missing.png"
        return [{"id": "mat-missing", "fileName": missing.name, "path": str(missing), "role": "main-product"}]
    if case.asset_mode == "invalid_assets":
        invalid = asset_dir / f"{case.case_id}-invalid.png"
        invalid.write_text("this is not a valid image file", encoding="utf-8")
        return [{"id": "mat-invalid", "fileName": invalid.name, "path": str(invalid), "role": "main-product"}]

    materials = []
    for index in range(case.image_count):
        path = asset_dir / f"{case.case_id}-{index + 1}.png"
        draw_product_image(path, case, index)
        materials.append({"id": f"mat-{index + 1}", "fileName": path.name, "path": str(path), "role": "main-product" if index == 0 else "detail"})
    return materials


def draw_product_image(path: Path, case: ValidationCase, index: int) -> None:
    width = 1200 + (index % 2) * 180
    height = 1600 - (index % 2) * 120
    palettes = [
        ("#f6efe2", "#1f5c4d", "#d9b36c"),
        ("#eef3ef", "#2f4f4a", "#c18d52"),
        ("#f7f5ef", "#47382d", "#8db3a6"),
        ("#f3eadc", "#17231f", "#e0bd76"),
    ]
    bg, primary, accent = palettes[index % len(palettes)]
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title = get_font(54)
    small = get_font(34)
    draw.rounded_rectangle((width * 0.28, height * 0.18, width * 0.72, height * 0.72), radius=64, fill="#ffffff", outline=accent, width=8)
    draw.ellipse((width * 0.38, height * 0.28, width * 0.62, height * 0.46), fill=accent)
    draw.rounded_rectangle((width * 0.43, height * 0.46, width * 0.57, height * 0.66), radius=24, fill=primary)
    draw.line((width * 0.26, height * 0.78, width * 0.74, height * 0.78), fill=accent, width=5)
    draw.text((80, 78), case.product_name, fill="#17231f", font=title)
    draw.text((80, 150), case.category, fill=primary, font=small)
    draw.text((80, height - 140), f"{case.writing_style} / {case.platform}", fill="#5f5145", font=small)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=96)


def build_product(case: ValidationCase, materials: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": f"product-{case.case_id.lower()}",
        "name": case.product_name,
        "category": case.category,
        "description": f"{case.product_name}是一款面向日常靜心與禮品場景的 Temple 商品。",
        "sellingPoint": "質感包裝、容易使用、適合社群展示，能在短時間內說清楚商品價值。",
        "spiritualInfo": "以安定、祝福與陪伴為核心，不宣稱療效，不使用保證式語句。",
        "targetAudience": "重視生活儀式感、送禮質感與心靈陪伴的使用者",
        "materials": materials,
    }


def run_case(case: ValidationCase, run_root: Path, ffmpeg: Path | None) -> dict[str, Any]:
    project_dir = run_root / "projects" / case.case_id
    export_dir = run_root / "exports" / case.case_id
    project_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    started = time.perf_counter()
    timings: dict[str, float] = {}
    result: dict[str, Any] = {
        "caseId": case.case_id,
        "name": case.name,
        "expected": case.expected,
        "assetMode": case.asset_mode,
        "platform": case.platform,
        "duration": case.duration,
        "status": "UNKNOWN",
        "accepted": False,
        "failure": None,
        "startedAt": now_iso(),
    }
    try:
        materials = create_product_assets(case, project_dir)
        product = build_product(case, materials)
        t0 = time.perf_counter()
        project = generate_video_script_package(
            product,
            {"requirement": case.requirement, "platform": case.platform, "duration": case.duration},
            project_id=f"project-{case.case_id.lower()}",
        )
        project["id"] = f"project-{case.case_id.lower()}"
        project["productId"] = product["id"]
        project["projectDir"] = str(project_dir)
        project["outputDir"] = str(export_dir)
        timings["scriptSeconds"] = round(time.perf_counter() - t0, 4)

        if not ffmpeg and case.expected == "production_export":
            raise RuntimeError("FFmpeg is unavailable; production export cannot be validated.")

        t0 = time.perf_counter()
        visual_report = run_image_pipeline(project, product, project_dir, emma_root=project_dir / "emma")
        timings["imageSeconds"] = round(time.perf_counter() - t0, 4)
        project["storyboard"] = visual_report.get("storyboard", {})
        project["providerPrompts"] = visual_report.get("providerPrompts", {})
        project["visualQuality"] = visual_report.get("quality", {})
        project["assetIndex"] = visual_report.get("assetIndex")

        if case.expected != "production_export":
            result["status"] = "UNEXPECTED_EXPORT_READY"
            result["accepted"] = False
            result["failure"] = classify_failure(RuntimeError("Input failure was expected but visual generation continued."), case)
            return finalize_case_result(result, project_dir, export_dir, timings, started)

        t0 = time.perf_counter()
        video_report = run_video_generation_pipeline(project, product, export_dir, project_dir, ffmpeg, preview=False)
        timings["videoSeconds"] = round(time.perf_counter() - t0, 4)
        project["finalVideo"] = str(export_dir / "final_video.mp4")
        project["videoIntelligence"] = video_report
        project["videoQuality"] = video_report.get("quality", {})
        project["videoSpec"] = "1080x1920 MP4, local FFmpeg motion pipeline"

        t0 = time.perf_counter()
        write_validation_export_package(project, product, export_dir)
        quality = evaluate_export(export_dir, str(ffmpeg) if ffmpeg else None)
        timings["qualitySeconds"] = round(time.perf_counter() - t0, 4)
        result["quality"] = summarize_quality(quality)
        result["status"] = "PASS" if quality["overall"] == "PASS" else "FAIL"
        result["accepted"] = quality["overall"] == "PASS"
        if not result["accepted"]:
            result["failure"] = classify_quality_failure(quality, case)
    except Exception as exc:
        failure = classify_failure(exc, case)
        result["failure"] = failure
        if case.expected == "handled_input_failure" and failure["category"] == "input-validation":
            result["status"] = "HANDLED_EXPECTED_FAILURE"
            result["accepted"] = True
        else:
            result["status"] = "FAIL"
            result["accepted"] = False
    return finalize_case_result(result, project_dir, export_dir, timings, started)


def summarize_quality(report: dict[str, Any]) -> dict[str, Any]:
    failed = report.get("failedChecks", [])
    return {
        "overall": report.get("overall"),
        "failedCount": len(failed),
        "failedChecks": [item.get("name") for item in failed[:8]],
    }


def write_validation_export_package(project: dict[str, Any], product: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "narration.txt": project.get("script", ""),
        "caption.txt": project.get("caption", ""),
        "thumbnail_suggestion.txt": project.get("thumbnailSuggestion", ""),
        "materials_used.txt": "\n".join(f"{item.get('fileName')} | {item.get('path')}" for item in product.get("materials", [])),
    }
    for name, text in files.items():
        (output_dir / name).write_text(str(text), encoding="utf-8")
    json_files = {
        "metadata.json": project.get("metadata", {}),
        "scenes.json": project.get("scenes", []),
        "prompts.json": project.get("prompts", []),
        "storyboard.json": project.get("storyboard", {}),
        "provider_prompts.json": project.get("providerPrompts", {}),
        "visual_quality.json": project.get("visualQuality", {}),
        "video_intelligence.json": project.get("videoIntelligence", {}),
        "video_quality.json": project.get("videoQuality", {}),
        "temple_os.json": build_temple_os_export(),
        "emma_core.json": build_emma_export(project),
    }
    for name, payload in json_files.items():
        (output_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    asset_index = project.get("assetIndex")
    if asset_index and Path(asset_index).exists():
        shutil.copyfile(asset_index, output_dir / "asset_index.json")
    else:
        (output_dir / "asset_index.json").write_text("{}", encoding="utf-8")


def build_emma_export(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "infrastructure-ready",
        "sceneUsage": [
            {
                "sceneId": scene.get("id"),
                "required": scene.get("emmaCore", {}).get("required", False),
                "referenceSelection": scene.get("emmaCore", {}).get("referenceSelection", {}).get("overall"),
                "consistency": scene.get("emmaCore", {}).get("consistency", {}).get("overall"),
            }
            for scene in project.get("scenes", [])
        ],
    }


def build_temple_os_export() -> dict[str, Any]:
    return {
        "schema": "temple-ai-studio.os-status.v1",
        "mode": "validation-summary",
        "root": str(REPO_ROOT),
        "validationVersion": VALIDATION_VERSION,
        "generatedAt": now_iso(),
        "note": "Validation export intentionally avoids mutating operations state.",
    }


def classify_failure(exc: Exception, case: ValidationCase) -> dict[str, Any]:
    message = str(exc)
    lower = message.lower()
    if "no product reference images" in lower or "cannot identify image file" in lower or "generated scene image is missing" in lower:
        category = "input-validation" if case.expected == "handled_input_failure" else "asset-processing"
        root = "Product image assets are missing or invalid."
        suggested = "Show a clear operator message and require valid product photos before generation."
    elif "ffmpeg" in lower or "render" in lower or "concat" in lower:
        category = "rendering"
        root = "Video rendering or FFmpeg validation failed."
        suggested = "Run diagnostics for FFmpeg path, codec fallback, and generated scene media."
    elif "emma" in lower:
        category = "emma-consistency"
        root = "Emma reference coverage or consistency gate failed."
        suggested = "Provide approved Emma references or disable Emma-required scene mode for product-only videos."
    else:
        category = "system"
        root = "Unhandled pipeline exception."
        suggested = "Inspect the case logs and add targeted recovery for this failure class."
    return {
        "category": category,
        "rootCause": root,
        "severity": case.severity_if_fail,
        "message": message[:1000],
        "suggestedFix": suggested,
    }


def classify_quality_failure(report: dict[str, Any], case: ValidationCase) -> dict[str, Any]:
    failed = [item.get("name", "") for item in report.get("failedChecks", [])]
    if any("text-quality" in item for item in failed):
        category = "content-quality"
        root = "Generated text package failed readability or encoding checks."
        suggested = "Repair Traditional Chinese generation output and rerun export quality validation."
    elif any("ffmpeg" in item for item in failed):
        category = "rendering"
        root = "Final MP4 failed playback validation."
        suggested = "Inspect FFmpeg output and retry rendering with codec fallback."
    else:
        category = "export-package"
        root = "Required export package files are missing or invalid."
        suggested = "Repair export package writer or upstream report serialization."
    return {
        "category": category,
        "rootCause": root,
        "severity": case.severity_if_fail,
        "message": ", ".join(failed[:10]),
        "suggestedFix": suggested,
    }


def finalize_case_result(
    result: dict[str, Any],
    project_dir: Path,
    export_dir: Path,
    timings: dict[str, float],
    started: float,
) -> dict[str, Any]:
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    timings["totalSeconds"] = round(time.perf_counter() - started, 4)
    result["finishedAt"] = now_iso()
    result["timings"] = timings
    result["memory"] = {"tracemallocPeakBytes": peak, "tracemallocCurrentBytes": current}
    result["disk"] = {"projectBytes": directory_size(project_dir), "exportBytes": directory_size(export_dir)}
    result["paths"] = {"projectDir": str(project_dir), "exportDir": str(export_dir)}
    return result


def run_concurrent_probe(cases: list[ValidationCase], run_root: Path, ffmpeg: Path | None) -> dict[str, Any]:
    probe_cases = [case for case in cases if case.expected == "production_export"][:3]
    if len(probe_cases) < 3:
        return {"overall": "SKIPPED", "reason": "Not enough valid cases for concurrent probe."}
    probe_root = run_root / "concurrent-probe"
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_case, case, probe_root, ffmpeg) for case in probe_cases]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = round(time.perf_counter() - start, 4)
    return {
        "overall": "PASS" if all(item.get("accepted") for item in results) else "FAIL",
        "elapsedSeconds": elapsed,
        "projectCount": len(results),
        "accepted": sum(1 for item in results if item.get("accepted")),
        "caseIds": [item["caseId"] for item in results],
    }


def analyze_failures(results: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [item for item in results if item.get("failure")]
    by_category: dict[str, dict[str, Any]] = {}
    for item in failures:
        failure = item["failure"]
        key = failure["category"]
        bucket = by_category.setdefault(
            key,
            {
                "category": key,
                "count": 0,
                "severity": failure["severity"],
                "rootCauses": {},
                "suggestedFix": failure.get("suggestedFix", "Inspect this failure class and add a targeted recovery."),
                "examples": [],
            },
        )
        bucket["count"] += 1
        root_cause = failure.get("rootCause", "Unspecified root cause.")
        bucket["rootCauses"][root_cause] = bucket["rootCauses"].get(root_cause, 0) + 1
        if len(bucket["examples"]) < 5:
            bucket["examples"].append(
                {
                    "caseId": item.get("caseId"),
                    "status": item.get("status", "UNKNOWN"),
                    "message": failure.get("message", ""),
                }
            )
    return {
        "totalFailures": len(failures),
        "unexpectedFailures": sum(1 for item in results if not item.get("accepted")),
        "byCategory": sorted(by_category.values(), key=lambda value: value["count"], reverse=True),
    }


def build_acceptance_results(results: list[dict[str, Any]], concurrent_probe: dict[str, Any]) -> dict[str, Any]:
    valid = [item for item in results if item["expected"] == "production_export"]
    expected_failures = [item for item in results if item["expected"] == "handled_input_failure"]
    export_pass = [item for item in valid if item.get("accepted")]
    handled = [item for item in expected_failures if item.get("accepted")]
    checks = [
        ("script-engine", all("scriptSeconds" in item.get("timings", {}) for item in results), "All cases create or attempt a script package."),
        ("image-pipeline", all(item.get("accepted") or item.get("failure") for item in results), "Visual generation passes or fails with classification."),
        ("video-pipeline", len(export_pass) == len(valid), "All valid cases export playable MP4 files."),
        ("quality-analyzer", all(item.get("quality") or item.get("failure") for item in results), "Each case produces a quality result or classified failure."),
        ("input-recovery", len(handled) == len(expected_failures), "Missing, empty, and invalid assets are handled without crash."),
        ("concurrent-projects", concurrent_probe.get("overall") == "PASS", "Three valid projects complete concurrently."),
    ]
    return {
        "overall": "PASS" if all(item[1] for item in checks) else "FAIL",
        "checks": [{"capability": name, "pass": ok, "criterion": criterion} for name, ok, criterion in checks],
    }


def build_reliability_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    valid = [item for item in results if item["expected"] == "production_export"]
    expected_failures = [item for item in results if item["expected"] == "handled_input_failure"]
    accepted = [item for item in results if item.get("accepted")]
    valid_success = [item for item in valid if item.get("accepted")]
    handled = [item for item in expected_failures if item.get("accepted")]
    crashes = [item for item in results if (item.get("failure") or {}).get("category") == "system"]
    retries = []
    for item in results:
        quality = item.get("quality") or {}
        if quality.get("failedCount", 0):
            retries.append(item)
    return {
        "projectCount": total,
        "acceptedCount": len(accepted),
        "acceptedRate": round(len(accepted) / total, 4) if total else 0,
        "validProductionProjectCount": len(valid),
        "validProductionSuccessCount": len(valid_success),
        "validProductionSuccessRate": round(len(valid_success) / len(valid), 4) if valid else 0,
        "expectedFailureCount": len(expected_failures),
        "expectedFailureHandledCount": len(handled),
        "expectedFailureHandledRate": round(len(handled) / len(expected_failures), 4) if expected_failures else 1,
        "crashCount": len(crashes),
        "crashRate": round(len(crashes) / total, 4) if total else 0,
        "retrySignalCount": len(retries),
        "exportSuccessCount": len(valid_success),
    }


def build_performance_report(results: list[dict[str, Any]], concurrent_probe: dict[str, Any], started: float) -> dict[str, Any]:
    valid = [item for item in results if item["expected"] == "production_export"]
    totals = [item["timings"]["totalSeconds"] for item in results]
    valid_totals = [item["timings"]["totalSeconds"] for item in valid]
    export_bytes = [item["disk"]["exportBytes"] for item in results]
    peak_memory = [item["memory"]["tracemallocPeakBytes"] for item in results]
    return {
        "batchElapsedSeconds": round(time.perf_counter() - started, 4),
        "coldStartProjectSeconds": totals[0] if totals else 0,
        "warmStartAverageSeconds": safe_mean(totals[1:]),
        "singleProjectAverageSeconds": safe_mean(valid_totals),
        "singleProjectP95Seconds": percentile(valid_totals, 0.95),
        "allCasesAverageSeconds": safe_mean(totals),
        "averageExportBytes": round(statistics.mean(export_bytes), 2) if export_bytes else 0,
        "maxExportBytes": max(export_bytes) if export_bytes else 0,
        "peakTracemallocBytes": max(peak_memory) if peak_memory else 0,
        "concurrentProbe": concurrent_probe,
    }


def determine_readiness(acceptance: dict[str, Any], reliability: dict[str, Any], failures: dict[str, Any], performance: dict[str, Any]) -> dict[str, Any]:
    critical_failures = [
        item
        for item in failures.get("byCategory", [])
        if item.get("severity") == "critical" and item.get("category") not in {"input-validation"}
    ]
    valid_success = reliability["validProductionSuccessRate"]
    handled = reliability["expectedFailureHandledRate"]
    crash = reliability["crashRate"]
    acceptance_pass = acceptance["overall"] == "PASS"
    if acceptance_pass and valid_success >= 0.98 and handled >= 1 and crash == 0 and not critical_failures:
        level = "PRODUCTION READY"
    elif valid_success >= 0.92 and handled >= 0.95 and crash <= 0.01:
        level = "RC"
    elif valid_success >= 0.80 and handled >= 0.90 and crash <= 0.03:
        level = "BETA"
    else:
        level = "NOT READY"
    return {
        "level": level,
        "criteria": {
            "acceptancePass": acceptance_pass,
            "validProductionSuccessRate": valid_success,
            "expectedFailureHandledRate": handled,
            "crashRate": crash,
            "criticalFailureCount": len(critical_failures),
            "averageProductionSeconds": performance.get("singleProjectAverageSeconds", 0),
        },
    }


def write_reports(
    report_dir: Path,
    run_root: Path,
    cases: list[ValidationCase],
    results: list[dict[str, Any]],
    acceptance: dict[str, Any],
    failures: dict[str, Any],
    reliability: dict[str, Any],
    performance: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "production-validation-summary.json": {
            "schema": VALIDATION_SCHEMA,
            "version": VALIDATION_VERSION,
            "createdAt": now_iso(),
            "artifactRoot": str(run_root),
            "caseCount": len(cases),
            "cases": [case.__dict__ for case in cases],
            "results": results,
        },
        "acceptance-results.json": acceptance,
        "failure-analysis.json": failures,
        "reliability-report.json": reliability,
        "performance-report.json": performance,
        "production-readiness-report.json": readiness,
    }
    paths = {}
    for name, payload in payloads.items():
        path = report_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[name] = str(path)
    dashboard = report_dir / "acceptance-dashboard.md"
    dashboard.write_text(build_dashboard(run_root, results, acceptance, failures, reliability, performance, readiness), encoding="utf-8")
    paths["acceptance-dashboard.md"] = str(dashboard)
    return paths


def build_dashboard(
    run_root: Path,
    results: list[dict[str, Any]],
    acceptance: dict[str, Any],
    failures: dict[str, Any],
    reliability: dict[str, Any],
    performance: dict[str, Any],
    readiness: dict[str, Any],
) -> str:
    failed_cases = [item for item in results if not item.get("accepted")]
    lines = [
        "# Temple AI Studio Production Validation Dashboard",
        "",
        f"- Generated: {now_iso()}",
        f"- Artifact root: `{run_root}`",
        f"- Readiness: **{readiness['level']}**",
        f"- Accepted cases: {reliability['acceptedCount']} / {reliability['projectCount']} ({reliability['acceptedRate']:.2%})",
        f"- Valid production success: {reliability['validProductionSuccessCount']} / {reliability['validProductionProjectCount']} ({reliability['validProductionSuccessRate']:.2%})",
        f"- Expected failure handling: {reliability['expectedFailureHandledCount']} / {reliability['expectedFailureCount']} ({reliability['expectedFailureHandledRate']:.2%})",
        f"- Crash rate: {reliability['crashRate']:.2%}",
        "",
        "## Acceptance",
        "",
        "| Capability | Result | Criterion |",
        "| --- | --- | --- |",
    ]
    for check in acceptance["checks"]:
        lines.append(f"| {check['capability']} | {'PASS' if check['pass'] else 'FAIL'} | {check['criterion']} |")
    lines.extend(
        [
            "",
            "## Reliability",
            "",
            f"- Export success count: {reliability['exportSuccessCount']}",
            f"- Retry signal count: {reliability['retrySignalCount']}",
            f"- Unexpected failure count: {failures['unexpectedFailures']}",
            "",
            "## Performance",
            "",
            f"- Batch elapsed seconds: {performance['batchElapsedSeconds']}",
            f"- Cold start project seconds: {performance['coldStartProjectSeconds']}",
            f"- Warm start average seconds: {performance['warmStartAverageSeconds']}",
            f"- Production project average seconds: {performance['singleProjectAverageSeconds']}",
            f"- Production project p95 seconds: {performance['singleProjectP95Seconds']}",
            f"- Concurrent probe: {performance['concurrentProbe'].get('overall')}",
            "",
            "## Known Issues",
            "",
        ]
    )
    if not failed_cases:
        lines.append("- No remaining blocker from this validation run.")
    else:
        for item in failed_cases[:20]:
            failure = item.get("failure") or {}
            lines.append(f"- `{item['caseId']}`: {failure.get('category')} - {failure.get('rootCause')}")
    return "\n".join(lines) + "\n"


def run_validation(count: int, artifact_root: Path, report_root: Path, skip_concurrent_probe: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    current_run_id = run_id()
    run_root = artifact_root / current_run_id
    report_dir = report_root
    ffmpeg_value = detect_ffmpeg(None)
    ffmpeg = Path(ffmpeg_value) if ffmpeg_value else None
    cases = build_cases(count)
    results = []
    for index, case in enumerate(cases, start=1):
        case_result = run_case(case, run_root, ffmpeg)
        case_result["ordinal"] = index
        results.append(case_result)
        print(json.dumps({"case": case.case_id, "status": case_result["status"], "accepted": case_result["accepted"]}, ensure_ascii=False))
    concurrent_probe = {"overall": "SKIPPED", "reason": "Skipped by command option."}
    if not skip_concurrent_probe:
        concurrent_probe = run_concurrent_probe(cases, run_root, ffmpeg)
    acceptance = build_acceptance_results(results, concurrent_probe)
    failures = analyze_failures(results)
    reliability = build_reliability_report(results)
    performance = build_performance_report(results, concurrent_probe, started)
    readiness = determine_readiness(acceptance, reliability, failures, performance)
    paths = write_reports(report_dir, run_root, cases, results, acceptance, failures, reliability, performance, readiness)
    return {
        "schema": VALIDATION_SCHEMA,
        "version": VALIDATION_VERSION,
        "createdAt": now_iso(),
        "runId": current_run_id,
        "artifactRoot": str(run_root),
        "reportDir": str(report_dir),
        "reportPaths": paths,
        "acceptance": acceptance,
        "failures": failures,
        "reliability": reliability,
        "performance": performance,
        "readiness": readiness,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Temple AI Studio product validation.")
    parser.add_argument("--count", type=int, default=DEFAULT_CASE_COUNT)
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--report-root", default=str(REPORT_ROOT))
    parser.add_argument("--skip-concurrent-probe", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    summary = run_validation(args.count, Path(args.artifact_root), Path(args.report_root), args.skip_concurrent_probe)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["readiness"]["level"] in {"RC", "PRODUCTION READY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
