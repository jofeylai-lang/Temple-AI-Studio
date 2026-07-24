# Provider Evaluation Matrix V1

Status: Active Standard

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`
- `BENCHMARK_PROTOCOL_V1.md`

## Purpose

Prevent premature provider replacement and provide a repeatable evaluation method.

## Required Comparison

Every provider decision must compare:

| Category | Required Question |
| --- | --- |
| Current solution | What do we already have working? |
| Better local solution | Can the current local path be improved without paid services? |
| Free API | Is there a reputable free API or free tier that materially improves quality? |
| Paid API | Is paid quality clearly superior enough to justify cost and CEO approval? |

## Evaluation Criteria

| Criterion | Measurement |
| --- | --- |
| Quality | Visual/audio/text output score and failure rate |
| Speed | End-to-end generation time |
| VRAM | Peak VRAM where relevant |
| Stability | Crash rate, failed job rate, recovery quality |
| Consistency | Similar input produces consistent output |
| Reproducibility | Same seed/settings can reproduce or approximate output |
| Cost | Local hardware, credits, subscription or API pricing |
| Privacy | What data leaves local machine |
| Maintenance | Install/update complexity |
| Windows Fit | Runs cleanly on CEO environment |
| Operator Burden | Whether CEO must touch technical settings |

## Current Provider Baselines

### FFmpeg

Status:

Active baseline.

Role:

Local video assembly, transcode, export and playback validation.

Replacement:

Not under consideration.

### ComfyUI

Status:

Candidate local generation provider.

Rule:

Do not replace or dismiss until latest workflows, nodes, plugins, models and community techniques are benchmarked.

### Whisper

Status:

Candidate local subtitle/transcription provider.

Rule:

Benchmark subtitle alignment and Traditional Chinese correction before paid transcription.

### GPT-SoVITS

Status:

Candidate local voice identity provider.

Rule:

Requires benchmark for voice consistency, training burden and output stability.

### LivePortrait

Status:

Candidate Emma/talking-head motion provider.

Rule:

Benchmark identity preservation before full adoption.

### MuseTalk

Status:

Candidate lip-sync/talking-head provider.

Rule:

Benchmark against LivePortrait or current local path before adoption.

## CEO Approval Required

CEO approval is required before:

- paid API activation
- external account billing
- upload of private source materials to third-party services
- provider migration that changes business workflow

## Definition Of Done

A provider decision is complete when the matrix is filled, benchmark evidence exists and the recommendation is constitution-compliant.
