# Validation Rules V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This validation rule set follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `QUALITY_CHECKLIST_V1.md`

## Purpose

This document defines product validation rules for V1.

It does not define code, APIs, schemas, or implementation logic.

## Validation Categories

### Required Input Rules

A project cannot proceed to generation unless:

- Product name exists.
- Product description exists.
- Main selling point exists.
- Target platform is selected.
- At least one product photo exists.
- Chinese video description exists.

### Content Rules

A generated content package is invalid if:

- It lacks a hook.
- It lacks product introduction.
- It lacks product features.
- It lacks spiritual value.
- It lacks CTA.
- It lacks ending.
- It changes product identity without user approval.
- It uses aggressive or exaggerated claims.

### Scene Rules

Each scene must have:

- Purpose
- Duration
- Visual goal or description
- Narration
- Subtitle
- Prompt direction
- Music direction
- Transition direction

Approved scenes cannot be changed unless the user requests regeneration or editing.

### Brand Rules

Temple content must:

- Use calm, clear, warm, premium language.
- Avoid fear-based selling.
- Avoid unverifiable spiritual promises.
- Keep CTA gentle.
- Use Traditional Chinese by default.

### Platform Rules

V1 target output must be:

- Vertical 9:16
- Reviewable before export
- Prepared for manual posting

Supported V1 platform targets:

- Instagram Reels
- TikTok
- YouTube Shorts
- Shorts

### Metadata Rules

Every project must include:

- Project id
- Product name
- Created date
- Target platform
- Source image reference
- Scene count
- Prompt version or category references
- Provider path when known
- Review status
- Export status

### Regeneration Rules

The system should allow regeneration of:

- One scene
- Hook
- Narration
- Subtitle
- Caption
- CTA
- Thumbnail suggestion
- SEO keywords

The system should not regenerate the full video unless:

- User requests full regeneration
- Product direction changes
- Main product image changes
- Target platform changes
- User rejects the full draft

### Export Rules

Export can proceed only when:

- Preview exists.
- User approval exists.
- Caption exists.
- Subtitle text exists or user has excluded subtitles.
- Metadata exists.
- Export target is selected.

## Definition of Done

Validation Rules V1 is complete when:

1. Required input rules are defined.
2. Content rules are defined.
3. Scene rules are defined.
4. Brand rules are defined.
5. Platform rules are defined.
6. Metadata rules are defined.
7. Regeneration rules are defined.
8. Export rules are defined.
9. Rules align with `QUALITY_CHECKLIST_V1.md`.
