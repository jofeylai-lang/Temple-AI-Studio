from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Any


COMMON_SCRIPT = (
    "嗨，我是 Emma。今天想帶你一起看看神殿裡很有溫度的小物。"
    "每一件作品都有自己的故事，也希望在忙碌生活中，陪你留下一點安定和好心情。"
    "等等我會用最簡單的方式，分享它的特色、適合的場合，還有日常可以怎麼使用。"
    "準備好了嗎？找個舒服的位置，我們一起慢慢開始吧。"
)
VOICE_DESIGNS = [
    (
        26072401,
        "Original adult female synthetic voice. Natural Taiwan Mandarin. Warm, bright, lively, "
        "and slightly playful lifestyle-vlog delivery with a gentle smile. Conversational pacing, "
        "clear but unforced diction. No Mainland China accent, announcer voice, sales voice, or "
        "imitation of an identifiable person.",
    ),
    (
        26072402,
        "Original adult female synthetic voice. Natural Taiwan Mandarin. Soft, warm and intimate, "
        "like a friendly lifestyle vlogger speaking to one viewer. Calm energy with a subtle smile. "
        "No Mainland China accent, broadcast tone, exaggerated cuteness, or imitation of any person.",
    ),
    (
        26072403,
        "Original adult female synthetic voice. Natural Taiwan Mandarin. Lively, expressive and "
        "slightly playful with light spontaneous energy, while remaining commercially clear and "
        "natural. No Mainland China accent, announcer style, cartoon voice, or real-person imitation.",
    ),
    (
        26072404,
        "Original adult female synthetic voice. Natural Taiwan Mandarin. Confident and polished but "
        "conversational, warm and approachable, suitable for premium lifestyle product videos. "
        "No Mainland China accent, newsreader delivery, hard-selling tone, or person imitation.",
    ),
    (
        26072405,
        "Original adult female synthetic voice. Natural Taiwan Mandarin. Calm, luminous and sincere "
        "with a light playful smile and relaxed vlog rhythm. Clear Taiwan phrasing without sounding "
        "formal. No Mainland China accent, announcer tone, or imitation of an identifiable person.",
    ),
]


def install_numba_compatibility_shim() -> None:
    if "numba" in sys.modules:
        return
    module = types.ModuleType("numba")

    def decorator(*args, **_kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda function: function

    module.jit = decorator
    module.njit = decorator
    module.guvectorize = decorator
    module.vectorize = decorator
    module.stencil = decorator
    module.prange = range
    sys.modules["numba"] = module


def wav_metrics(path: Path) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(str(path), always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sample_rate
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
    silence = float(np.mean(np.abs(audio) < 0.003)) if len(audio) else 1.0
    return {
        "durationSeconds": round(duration, 3),
        "sampleRate": int(sample_rate),
        "channels": 1,
        "peak": round(peak, 5),
        "rms": round(rms, 5),
        "silenceRatio": round(silence, 5),
        "durationPass": 20 <= duration <= 30,
        "clippingPass": peak < 0.999,
        "signalPass": rms >= 0.01 and silence < 0.6,
    }


def write_comparison_html(output_dir: Path, records: list[dict[str, Any]]) -> Path:
    cards = "\n".join(
        (
            f"<section><h2>Emma 聲線 {record['number']}</h2>"
            f"<audio controls preload=\"metadata\" src=\"{Path(record['path']).name}\"></audio>"
            f"<p>長度 {record['metrics']['durationSeconds']} 秒，取樣率 "
            f"{record['metrics']['sampleRate']} Hz</p></section>"
        )
        for record in records
    )
    html = f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Emma 原創合成聲線比較</title>
<style>
body {{ max-width: 760px; margin: 40px auto; padding: 0 20px; font-family: sans-serif; color: #202124; }}
section {{ padding: 18px 0; border-bottom: 1px solid #ddd; }}
audio {{ width: 100%; }}
p {{ color: #5f6368; }}
</style>
</head>
<body>
<h1>Emma 原創合成聲線比較</h1>
<p>五個樣本使用完全相同的台灣華語文稿，皆為原創合成聲線，未模仿任何真人。</p>
{cards}
</body>
</html>
"""
    path = output_dir / "Emma_五聲線比較.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate five original synthetic Emma voice candidates.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    install_numba_compatibility_shim()

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        str(Path(args.model).resolve()),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    records = []
    for number, (seed, instruction) in enumerate(VOICE_DESIGNS, start=1):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        wavs, sample_rate = model.generate_voice_design(
            text=COMMON_SCRIPT,
            language="Chinese",
            instruct=instruction,
        )
        output = output_dir / f"Emma_原創聲線_{number}.wav"
        sf.write(str(output), wavs[0], sample_rate)
        metrics = wav_metrics(output)
        records.append(
            {
                "number": number,
                "path": str(output),
                "seed": seed,
                "script": COMMON_SCRIPT,
                "instruction": instruction,
                "metrics": metrics,
                "provenance": "Qwen3-TTS-12Hz-1.7B-VoiceDesign real local generation",
                "realPersonImitation": False,
            }
        )
    overall = "PASS" if all(
        record["metrics"]["durationPass"]
        and record["metrics"]["clippingPass"]
        and record["metrics"]["signalPass"]
        for record in records
    ) else "FAIL"
    report = {
        "schema": "temple-ai-studio.emma-synthetic-voice-candidates.v1",
        "overall": overall,
        "model": str(Path(args.model).resolve()),
        "language": "zh-TW",
        "paidCostTwd": 0,
        "identicalScript": True,
        "candidates": records,
    }
    report_path = output_dir / "Emma_五聲線比較報告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = write_comparison_html(output_dir, records)
    print(
        json.dumps(
            {
                "overall": overall,
                "report": str(report_path),
                "comparison": str(html_path),
                "candidates": [record["path"] for record in records],
            },
            ensure_ascii=False,
        )
    )
    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
