# Acceptance Test Plan V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This acceptance test plan follows:

- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `QUALITY_CHECKLIST_V1.md`
- `VALIDATION_RULES_V1.md`
- `WORKFLOW_SPEC_V1.md`

## Purpose

This document defines how V1 should be accepted.

It does not define automated tests, code, APIs, or implementation details.

## Acceptance Scenario

The V1 product is accepted when a user can create three Temple product video packages from different products or product briefs.

Each package must include:

- Product information
- Product photo reference
- Chinese description
- Story plan
- Scene plan
- Narration
- Subtitles
- Caption
- Thumbnail suggestion
- Metadata
- Preview or export-ready package
- Review status

## Test Case 1: New Product Video

Goal:

Create a new product video from a new product.

Pass criteria:

- Product is created.
- Required inputs pass validation.
- Scene plan is generated.
- Preview is reviewable.
- Export package is prepared after approval.

## Test Case 2: Existing Product Video

Goal:

Create a new video from an existing product.

Pass criteria:

- Product Library selection works conceptually.
- Existing product materials are reused.
- New Chinese description creates a new project.
- Prior product identity remains stable.

## Test Case 3: Single-Scene Regeneration

Goal:

Fix one weak scene without changing approved scenes.

Pass criteria:

- One scene is selected.
- User revision note is captured.
- Only affected scene content changes.
- Previous version can be restored conceptually.

## Test Case 4: Failure Recovery

Goal:

Recover from failed preview or export.

Pass criteria:

- Failure state is clear.
- User work is preserved.
- Retry path is available.
- User does not need to restart from zero.

## Test Case 5: Brand and Quality Review

Goal:

Confirm content follows Temple Brand DNA.

Pass criteria:

- Tone is calm and premium.
- CTA is not aggressive.
- Spiritual claims are grounded.
- Subtitles are readable.
- Caption is usable for manual posting.

## Definition of Done

Acceptance Test Plan V1 is complete when the product has clear acceptance scenarios for new video creation, existing product reuse, scene regeneration, failure recovery, and brand quality.

