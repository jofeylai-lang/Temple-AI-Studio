# Current Capability Baseline V1

Status: Baseline Inventory

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`
- `AI_CAPABILITY_RESEARCH_AND_BENCHMARK_FRAMEWORK_V1.md`

## Purpose

Record what Temple AI Studio can benchmark today, before comparing better local, free or paid alternatives.

## Current Measured Baseline

Measured with:

```text
scripts/temple_ai_studio/quality_check.py
```

Input:

```text
D:\AI\Temple Product Video Generator\data\exports\project-20260724-11969a6e
```

Report:

```text
evaluations/quality-reviews/2026-07-24-v1-production-export-quality-report.json
```

Result:

```text
PASS
```

Measured facts:

- required export files present
- metadata JSON valid
- scenes JSON valid
- prompts JSON valid
- subtitles text quality passed
- narration text quality passed
- caption text quality passed
- thumbnail suggestion text quality passed
- FFmpeg decode passed
- resolution: 1080x1920
- duration: 00:00:24.00
- fps: 25

## Capability Baseline Table

| Capability | Current Implementation | Current Benchmark Status |
| --- | --- | --- |
| LLM | Codex/OpenAI-assisted engineering plus rule-based local app generation | Not directly benchmarked yet |
| Image Generation | Uploaded photos and generated placeholder frames | Not a true image generation provider |
| Identity Preservation | Governance rules only | Not benchmarkable until reference material/scorer exists |
| Character Training | None | Blocked by approved Emma source material |
| Video Generation | FFmpeg image assembly from source photos | Partially measured through V1 export quality check |
| Talking Head | None | Not benchmarked |
| Full Body Animation | None | Not benchmarked |
| Lip Sync | None | Not benchmarked |
| Voice Cloning | None | Not benchmarked |
| TTS | Text narration files only | Audio generation not benchmarked |
| Subtitle | Timeline-based SRT from scene durations | Partially measured through text and required-file checks |
| Editing | FFmpeg local rendering | Measured through decode, duration, resolution and file completeness |
| Music | None | Not benchmarked |
| Automation | V1 local workflow, backup, restore, support package, quality checker | Partially measured through production deployment and quality check |

## Replacement Eligibility

No capability is currently eligible for replacement recommendation.

Reasons:

- missing capabilities must first establish a baseline or candidate benchmark
- current FFmpeg editing path has not reached practical limits
- ComfyUI has not been fully benchmarked with latest workflows
- Emma identity workflows are blocked by source material
- voice and lip-sync workflows have not been benchmarked

## Immediate Benchmark Priorities

1. Editing and subtitle baseline expansion using existing V1 exports.
2. ComfyUI image generation baseline.
3. ComfyUI/LTX/Wan video generation feasibility.
4. Whisper/faster-whisper subtitle alignment baseline.
5. LivePortrait/MuseTalk talking-head baseline after identity references exist.
6. GPT-SoVITS/OpenVoice/Coqui voice baseline after approved voice material exists.

## Definition Of Done

Current Capability Baseline V1 is complete when all current implementations are listed and no replacement decision is made without a measured practical limit.
