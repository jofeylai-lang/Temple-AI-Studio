# Master Project OS Foundation V1

Status: Active Foundation

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`
- Master Project instruction from CEO

## Objective

Turn Temple AI Studio from a single completed product into an AI Content Operating System.

Temple Product Video Generator V1 remains frozen except for bug fixes.

New work should build shared operating-system capabilities that future products can reuse.

## Current Baseline

Completed:

- Temple Product Video Generator V1
- Production installation
- V1 release tag
- Constitution
- GitHub remote synchronization

Active strategic direction:

```text
One Traditional Chinese sentence
-> intent understanding
-> research
-> script
-> storyboard
-> Emma or product visuals
-> voice
-> subtitles
-> editing
-> quality analysis
-> targeted regeneration
-> platform-ready export
```

## OS Modules

### 1. Request Understanding

Purpose:

Convert one Traditional Chinese sentence into structured production intent.

Outputs:

- content type
- product or character requirement
- target platform
- audience
- creative tone
- required source materials
- approval requirements

### 2. Research Engine

Purpose:

Research current tools, workflows, benchmarks, video trends and GitHub projects before technology decisions.

Outputs:

- research briefs
- source links
- assumptions
- risks
- recommended benchmark candidates

### 3. Script And Storyboard Engine

Purpose:

Create reusable scene plans from Temple business intent.

Outputs:

- hook
- scene list
- narration
- subtitle plan
- visual plan
- CTA
- platform format

### 4. Provider Evaluation System

Purpose:

Compare current solution, better local solution, free API and paid API before provider adoption.

Outputs:

- provider matrix
- benchmark report
- cost/privacy notes
- replacement proposal if justified

### 5. Asset Generation System

Purpose:

Generate or update images, video clips, Emma assets, voice and subtitles.

Required behavior:

- preserve approved assets
- regenerate only failed components
- preserve Emma identity
- track prompt and metadata lineage

### 6. Editing System

Purpose:

Assemble platform-ready videos with correct pacing, subtitles, CTA and export format.

Initial proven component:

- FFmpeg local MP4 rendering

Future components:

- scene timing optimizer
- subtitle style renderer
- audio mix
- platform-specific safe area checks

### 7. Quality Gate System

Purpose:

Automatically validate every generated video before CEO review.

Initial implementation:

```text
scripts/temple_ai_studio/quality_check.py
```

### 8. Knowledge Memory

Purpose:

Convert failures, CEO corrections, benchmark outcomes and provider lessons into reusable project knowledge.

Storage locations:

- `knowledge/`
- `research/`
- `evaluations/`
- `docs/`

## First Shared Implementation

Created:

```text
scripts/temple_ai_studio/quality_check.py
```

This is the first OS-level quality tool outside Temple Product Video Generator V1.

It checks:

- required export files
- JSON validity
- subtitle/caption/narration text quality
- mojibake indicators
- FFmpeg playback/decode
- vertical video format

## Near-Term Engineering Order

1. Establish research and benchmark records.
2. Measure the current local FFmpeg product-video export path.
3. Research current ComfyUI workflows before any replacement decision.
4. Create provider benchmark templates.
5. Create Emma identity governance before building Emma generation.
6. Build quality gates before adding more generators.
7. Build the next product only after shared quality and research loops exist.

## CEO Decision Gates

Ask CEO only for:

- paid provider activation
- business priority between next products
- Emma source material if unavailable
- destructive data operation
- administrator permission with no alternative
- creative direction ambiguity

## Definition Of Done

OS Foundation V1 is complete when:

- shared architecture is documented
- current research is recorded
- benchmark protocol exists
- quality gate protocol exists
- provider evaluation protocol exists
- Emma identity governance exists
- first reusable quality-check tool exists
- a real V1 export has been checked by the shared quality tool
