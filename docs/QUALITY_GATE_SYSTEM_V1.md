# Quality Gate System V1

Status: Active Standard

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`

## Purpose

Define automatic validation gates for Temple AI Studio content before CEO review.

## Required Video Quality Gates

Every generated video must validate:

- request alignment
- product correctness
- Emma identity where Emma appears
- voice identity and clarity where voice is used
- subtitle readability
- subtitle timing
- Traditional Chinese text quality
- editing rhythm
- scene order
- CTA presence
- platform format
- playback/decode quality
- export package completeness
- metadata completeness

## First Implemented Gate

Shared local export checker:

```text
scripts/temple_ai_studio/quality_check.py
```

Current checks:

- required export files
- JSON validity
- subtitle/caption/narration text quality
- mojibake indicators
- FFmpeg decode
- vertical video format

## Targeted Regeneration Rule

If one component fails, regenerate only that component whenever possible.

Examples:

- subtitle failure -> regenerate subtitle file only
- one scene failure -> regenerate that scene only
- playback failure -> rerender export only
- Emma identity failure -> regenerate visual/clip only, preserve approved script and audio
- voice failure -> regenerate voice only, preserve approved scenes

## Quality Report Storage

Quality reports should be stored in:

```text
evaluations/quality-reviews/
```

## Pass/Fail Rule

CEO review should receive only:

- PASS exports
- or FAIL reports with specific failed components and next repair action

The CEO should not receive raw debugging burden.

## Future Gates

Next quality gates to implement:

1. Emma identity similarity check.
2. Voice consistency check.
3. Subtitle safe-area check.
4. Hook timing check.
5. Scene duration rhythm check.
6. Product image presence check.
7. CTA detection.
8. Platform-specific export preset validation.

## Definition Of Done

Quality Gate System V1 is complete when a generated export can be checked automatically and failed components are reported in a structured format.
