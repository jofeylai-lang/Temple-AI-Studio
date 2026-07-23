# Prompt System V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This prompt system follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `QUALITY_CHECKLIST_V1.md`

## Purpose

This document defines how prompts are organized and governed for Temple product videos.

It does not include production prompts, prompt text, code, APIs, or implementation details.

## Prompt System Principles

1. Prompts must follow Temple Brand DNA.
2. Prompts must be traceable to product, scene, platform, and version.
3. Prompts must support scene-level regeneration.
4. Prompts must not bypass human review.
5. Prompts must not expand V1 scope beyond one product video workflow.

## Prompt Categories

### Intent Prompt Category

Purpose:

Analyze the user's Chinese request.

Output direction:

- Product type
- Target audience
- Marketing objective
- Tone
- Missing information

### Story Prompt Category

Purpose:

Create the video concept, outline, scene order, and emotional rhythm.

Output direction:

- Main message
- Scene count
- Scene order
- CTA direction
- Duration target

### Scene Prompt Category

Purpose:

Create per-scene planning.

Output direction:

- Scene purpose
- Duration
- Visual goal
- Narration goal
- Subtitle goal

### Visual Prompt Category

Purpose:

Prepare image and video generation guidance.

Output direction:

- Product visibility
- Composition
- Lighting
- Motion
- Mood
- Source image fidelity
- Platform-safe framing

### Narration Prompt Category

Purpose:

Prepare Traditional Chinese voiceover text.

Output direction:

- Speaking tone
- Sentence length
- Emotional temperature
- Product clarity

### Subtitle Prompt Category

Purpose:

Prepare concise readable subtitles.

Output direction:

- Short text
- Readable pacing
- Product or CTA emphasis when needed

### Caption Prompt Category

Purpose:

Prepare manual posting text.

Output direction:

- Traditional Chinese caption
- Optional hashtags
- SEO keywords
- No exaggerated claims

### Thumbnail Prompt Category

Purpose:

Prepare thumbnail suggestion.

Output direction:

- Best frame
- Product focus
- Cover text direction
- Brand presence

### Quality Review Prompt Category

Purpose:

Review output against `QUALITY_CHECKLIST_V1.md`.

Output direction:

- Pass/fail by category
- Weak scene identification
- Recommended regeneration target

## Prompt Governance

Every prompt output should preserve:

- Product name
- Project id
- Scene id when applicable
- Prompt category
- Prompt version
- Source document references
- Review status

Prompts should not:

- Change approved scenes without user approval
- Change product identity without user edit
- Create unsupported V1 features
- Make unverifiable spiritual or health claims
- Generate publishing actions

## Regeneration Support

Prompt categories that can regenerate independently:

- Hook
- Single scene
- Scene visual direction
- Scene narration
- Scene subtitle
- CTA
- Caption
- SEO keywords
- Thumbnail suggestion

Full prompt regeneration should only happen when the user rejects the full draft or changes product direction, platform, or main image.

## Definition of Done

Prompt System V1 is complete when:

1. Prompt categories are defined.
2. Each category maps to the reasoning pipeline.
3. Prompt governance protects Temple Brand DNA.
4. Scene-level regeneration is supported.
5. Prompt traceability is defined.
6. No actual production prompts, code, APIs, or implementation details are included.
