from __future__ import annotations

import argparse
import json
import re
import sys
import types
import wave
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def install_av_import_shim() -> None:
    # The host's application-control policy blocks PyAV's bundled DLLs. Audio is
    # decoded by the approved FFmpeg binary before this worker runs.
    if "av" not in sys.modules:
        sys.modules["av"] = types.ModuleType("av")


def read_pcm16(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError(f"Expected mono PCM16 WAV: {path}")
        sample_rate = source.getframerate()
        samples = np.frombuffer(
            source.readframes(source.getnframes()),
            dtype=np.int16,
        ).astype(np.float32)
    return samples / 32768.0, sample_rate


def normalized_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def transcript_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized_text(left), normalized_text(right)).ratio()


def run_transcription(
    model: Any,
    audio: np.ndarray,
    language: str,
    converter: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    segments, info = model.transcribe(
        audio,
        language=language,
        task="transcribe",
        beam_size=5,
        best_of=5,
        condition_on_previous_text=False,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={
            "threshold": 0.45,
            "min_speech_duration_ms": 250,
            "min_silence_duration_ms": 180,
            "speech_pad_ms": 100,
        },
        initial_prompt="台灣華語，神殿商品生活短影音。使用繁體中文。",
    )
    records = []
    for segment in segments:
        text = converter.convert(segment.text.strip())
        words = [
            {
                "start": round(float(word.start), 3),
                "end": round(float(word.end), 3),
                "word": converter.convert(word.word),
                "probability": round(float(word.probability), 5),
            }
            for word in (segment.words or [])
        ]
        records.append(
            {
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "durationSeconds": round(float(segment.end - segment.start), 3),
                "transcript": text,
                "avgLogProbability": round(float(segment.avg_logprob), 6),
                "noSpeechProbability": round(float(segment.no_speech_prob), 6),
                "compressionRatio": round(float(segment.compression_ratio), 6),
                "words": words,
            }
        )
    return records, {
        "language": info.language,
        "languageProbability": round(float(info.language_probability), 6),
        "durationSeconds": round(float(info.duration), 3),
        "durationAfterVadSeconds": round(float(info.duration_after_vad), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe canonical Emma voice sources.")
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8-sig"))
    install_av_import_shim()
    from faster_whisper import WhisperModel
    from opencc import OpenCC

    model = WhisperModel(
        job["modelPath"],
        device=job.get("device", "cpu"),
        compute_type=job.get("computeType", "int8"),
        local_files_only=True,
    )
    converter = OpenCC("s2twp")
    sources = []
    all_segments = []
    for source in job["sources"]:
        audio, sample_rate = read_pcm16(Path(source["audioPath"]))
        if sample_rate != 16000:
            raise ValueError(f"ASR source must be 16 kHz: {source['audioPath']}")
        segments, info = run_transcription(model, audio, "zh", converter)
        validated = []
        for index, segment in enumerate(segments, start=1):
            start_sample = max(0, int((segment["start"] - 0.08) * sample_rate))
            end_sample = min(len(audio), int((segment["end"] + 0.08) * sample_rate))
            verification, _ = run_transcription(
                model,
                audio[start_sample:end_sample],
                "zh",
                converter,
            )
            verification_text = "".join(item["transcript"] for item in verification)
            alignment = transcript_similarity(segment["transcript"], verification_text)
            word_coverage = (
                sum(max(0.0, word["end"] - word["start"]) for word in segment["words"])
                / max(segment["durationSeconds"], 0.001)
            )
            reasons = []
            if segment["durationSeconds"] < 2.5:
                reasons.append("speech-too-short")
            if segment["durationSeconds"] > 20:
                reasons.append("speech-too-long")
            if len(normalized_text(segment["transcript"])) < 3:
                reasons.append("transcript-too-short")
            if segment["avgLogProbability"] < -0.85:
                reasons.append("low-asr-confidence")
            if segment["noSpeechProbability"] > 0.35:
                reasons.append("speech-not-confident")
            if alignment < 0.78:
                reasons.append("transcript-alignment-failed")
            record = {
                **segment,
                "segmentId": f"{source['id']}-speech-{index:02d}",
                "sourceId": source["id"],
                "sourcePath": source["sourcePath"],
                "sourceSha256": source["sourceSha256"],
                "audioPath": source["audioPath"],
                "verificationTranscript": verification_text,
                "transcriptAlignment": round(alignment, 5),
                "wordTimestampCoverage": round(min(1.0, word_coverage), 5),
                "overall": "PASS" if not reasons else "REJECT",
                "reasons": reasons,
            }
            validated.append(record)
            all_segments.append(record)
        sources.append(
            {
                **source,
                "asr": info,
                "segments": validated,
            }
        )
    accepted = [item for item in all_segments if item["overall"] == "PASS"]
    report = {
        "schema": "temple-ai-studio.emma-canonical-voice-transcription.v1",
        "engine": "faster-whisper-large-v3-turbo",
        "modelPath": job["modelPath"],
        "language": "zh-TW",
        "traditionalChineseConversion": "OpenCC s2twp",
        "sources": sources,
        "segments": all_segments,
        "summary": {
            "sourceCount": len(sources),
            "segmentCount": len(all_segments),
            "acceptedSegments": len(accepted),
            "rejectedSegments": len(all_segments) - len(accepted),
            "acceptedSpeechSeconds": round(
                sum(item["durationSeconds"] for item in accepted),
                3,
            ),
        },
        "overall": "PASS" if accepted else "FAIL",
    }
    atomic_json(Path(args.output), report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
