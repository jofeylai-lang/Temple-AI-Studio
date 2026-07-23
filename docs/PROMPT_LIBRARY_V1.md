# Prompt Library V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This prompt library follows:

- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `PROMPT_SYSTEM_V1.md`
- `QUALITY_CHECKLIST_V1.md`
- `VALIDATION_RULES_V1.md`

## Purpose

This document defines V1 prompt templates at a product-planning level.

These are structured prompt briefs, not implementation code or API calls.

## Prompt Template Rules

Every prompt template must:

- Preserve Temple Brand DNA.
- Use Traditional Chinese for user-facing output.
- Keep product identity stable.
- Keep approved scenes stable.
- Support scene-level regeneration.
- Produce reviewable output.
- Avoid unverifiable spiritual claims.

## Template Inventory

### Intent Analysis Template

Purpose:

Understand the user's Chinese request.

Required output:

- Product type
- Target audience
- Marketing objective
- Desired tone
- Target platform
- Missing information

### Story Planning Template

Purpose:

Create video concept, scene order, emotional rhythm, duration target, and CTA direction.

Required output:

- Main message
- Scene count
- Scene order
- Emotional rhythm
- CTA direction

### Scene Planning Template

Purpose:

Create structured scene records.

Required output per scene:

- Purpose
- Duration
- Visual goal
- Narration goal
- Subtitle goal
- Music direction
- Transition direction

### Visual Direction Template

Purpose:

Prepare image/video generation guidance.

Required output:

- Product visibility
- Composition
- Lighting
- Background
- Motion
- Color direction
- Source material fidelity

### Narration Template

Purpose:

Create Traditional Chinese narration.

Required output:

- Scene narration
- Tone note
- Reading pace note

### Subtitle Template

Purpose:

Create readable Traditional Chinese subtitles.

Required output:

- Scene subtitle
- Shortened version when needed
- Readability note

### Caption Template

Purpose:

Create manual posting caption.

Required output:

- Caption
- Hashtags
- SEO keywords

### Thumbnail Suggestion Template

Purpose:

Create thumbnail direction.

Required output:

- Suggested frame
- Cover text direction
- Product focus
- Brand presence

### Quality Review Template

Purpose:

Check the generated package against V1 quality rules.

Required output:

- Pass/fail per category
- Weakest scene
- Recommended fix
- Export readiness

## Definition of Done

Prompt Library V1 is complete when all V1 prompt templates are named, scoped, traceable, and aligned with the prompt system.

