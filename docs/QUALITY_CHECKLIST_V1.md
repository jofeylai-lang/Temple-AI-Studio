# Quality Checklist V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This checklist follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `UX_FLOW_V1.md`

## Purpose

This document defines quality checks for every Temple product video before export.

It does not define code, automation rules, APIs, or implementation.

## Review Stages

### Stage 1: Input Readiness

Pass criteria:

- Product name exists.
- Product description exists.
- Main selling point exists.
- Target platform is selected.
- At least one product photo exists.
- Chinese video description exists.

Fail outcome:

Return to Create Video.

### Stage 2: Brand Fit

Pass criteria:

- Tone is calm, clear, warm, premium, and grounded.
- CTA is direct but gentle.
- Writing does not overpromise spiritual results.
- Content does not feel loud, cheap, manipulative, or fear-based.
- Visual direction follows Temple color identity.

Fail outcome:

Mark Needs Revision and regenerate or edit affected scenes.

### Stage 3: Content Structure

Pass criteria:

- Hook exists.
- Introduction exists.
- Product Features exist.
- Spiritual Value exists.
- Call To Action exists.
- Ending exists.
- Scene order is understandable.
- Emotional rhythm is coherent.

Fail outcome:

Regenerate story plan or affected scenes.

### Stage 4: Scene Completeness

Each scene must include:

- Purpose
- Estimated duration
- Visual description
- Narration
- Subtitle
- Prompt direction
- Music direction
- Transition direction
- Optional effects when relevant

Fail outcome:

Regenerate or complete the affected scene only.

### Stage 5: Text Quality

Pass criteria:

- Traditional Chinese is used.
- Sentences are short enough for social video.
- Subtitles are readable.
- Caption is ready for manual posting.
- SEO keywords exist.
- Thumbnail suggestion exists.

Fail outcome:

Regenerate text, subtitle, caption, or thumbnail suggestion independently.

### Stage 6: Preview Quality

Pass criteria:

- Product is visible when needed.
- Video is vertical 9:16.
- Duration matches selected target.
- Audio exists if narration is expected.
- Subtitles are present if selected.
- No obvious corrupted media.
- Preview is understandable without additional explanation.

Fail outcome:

Regenerate scene, retry generation, or mark failed with recovery instructions.

### Stage 7: Export Readiness

Pass criteria:

- User approved preview.
- Final platform is selected.
- Final MP4 name is confirmed.
- Caption is available.
- Metadata is complete.
- Export location is defined.

Fail outcome:

Return to Preview or Export.

## Review Status Rules

Draft:

Content exists but has not been reviewed.

Needs Revision:

One or more quality checks failed.

Approved:

User accepts the preview and content package.

Exported:

Final MP4 and support files are available.

Failed:

Generation or export failed, but recovery is possible.

## Definition of Done

Quality Checklist V1 is complete when every Temple product video can be reviewed against:

1. Input readiness
2. Brand fit
3. Content structure
4. Scene completeness
5. Text quality
6. Preview quality
7. Export readiness
8. Review status
