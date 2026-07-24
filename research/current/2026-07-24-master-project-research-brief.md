# Master Project Research Brief

Date: 2026-07-24

Status: Initial Current-State Scan

Purpose:

Support Temple AI Studio Master Project decisions with current research before opinion.

## Sources Reviewed

### ComfyUI

- Official GitHub: https://github.com/comfyanonymous/ComfyUI
- ComfyUI Manager: https://github.com/Comfy-Org/ComfyUI-Manager
- ComfyUI Docs: https://docs.comfy.org/

Initial finding:

ComfyUI remains a serious local workflow engine and should not be replaced without benchmark evidence. Current work should research workflows, manager-supported custom nodes, model loading, and reproducible graph execution before judging quality.

### FFmpeg

- Official website: https://ffmpeg.org/
- Official documentation: https://ffmpeg.org/documentation.html
- Official GitHub mirror: https://github.com/FFmpeg/FFmpeg

Initial finding:

FFmpeg remains the production baseline for local video assembly, transcode and playback validation. Temple AI Studio should continue using it as the first editing/rendering primitive while adding structured quality checks.

### Whisper

- Official GitHub: https://github.com/openai/whisper

Initial finding:

Whisper remains a useful local/open-source transcription baseline. For Temple AI Studio, Whisper should be benchmarked for subtitle alignment and correction workflows before introducing paid transcription.

### GPT-SoVITS

- Official GitHub: https://github.com/RVC-Boss/GPT-SoVITS

Initial finding:

GPT-SoVITS is a candidate for local voice identity workflows, but it must be benchmarked for voice consistency, training burden, language quality, latency and operator risk before adoption.

### LivePortrait

- Official GitHub: https://github.com/KwaiVGI/LivePortrait

Initial finding:

LivePortrait is relevant for portrait animation and potential Emma talking-head workflows. It should be benchmarked for identity preservation, mouth/face motion, temporal stability and source-image sensitivity before expansion.

### MuseTalk

- Official GitHub: https://github.com/TMElyralab/MuseTalk

Initial finding:

MuseTalk is relevant for audio-driven lip-sync/talking-head generation. It should be benchmarked against LivePortrait-style workflows before either is chosen for Emma.

### Short-Form Video Production

Sources:

- YouTube Shorts help and creator resources: https://support.google.com/youtube/
- TikTok Creative Center: https://ads.tiktok.com/business/creativecenter/
- TikTok Creative Center best practices: https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/en
- Meta/Instagram Reels ads and creative guidance: https://www.facebook.com/business/ads/reels-ad-format

Initial finding:

High-performing short-form video patterns consistently emphasize early hook, fast visual confirmation of topic, clear subtitles, mobile-first framing, retention pacing and explicit CTA. Temple videos should use these as reusable production rules, not as copied content.

## Current Engineering Decisions

### Decision 1: Do Not Replace ComfyUI

Disposition:

No replacement decision is allowed yet.

Reason:

The constitution requires research, benchmark and optimisation before replacement. Current evidence is insufficient to prove ComfyUI has reached practical limits.

### Decision 2: Keep FFmpeg As The Editing Baseline

Disposition:

Continue.

Reason:

FFmpeg is mature, local, free, scriptable and already proven in Temple Product Video Generator V1.

### Decision 3: Build Quality Gates Before More Generators

Disposition:

Implemented first shared tool:

```text
scripts/temple_ai_studio/quality_check.py
```

Reason:

One-click generation is unsafe without automatic validation and targeted regeneration.

### Decision 4: Treat Emma As A Governed Identity System

Disposition:

Define Emma identity governance before building Emma generation.

Reason:

Identity drift is a core product risk and cannot be fixed only at export time.

## Open Research Threads

1. Current best ComfyUI image-to-video workflows.
2. Current ComfyUI model/node set for product video and character motion.
3. Current local talking-head benchmarks: LivePortrait vs MuseTalk.
4. Current local voice benchmarks: GPT-SoVITS vs other free/local options.
5. Current subtitle styling patterns for Taiwan Traditional Chinese short-form video.
6. Current quality metrics for identity preservation and video coherence.

## Next Benchmark Candidates

- FFmpeg export validation baseline
- ComfyUI product-image generation workflow
- ComfyUI image-to-video workflow
- LivePortrait talking-head identity preservation
- MuseTalk lip-sync quality
- Whisper subtitle alignment
- GPT-SoVITS voice consistency

## Research Rule

This brief is not a final provider decision.

Every technology above must pass benchmark and optimisation before adoption or replacement.
