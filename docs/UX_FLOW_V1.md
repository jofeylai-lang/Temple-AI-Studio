# UX Flow V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This UX flow follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`

## Purpose

This document defines the user's experience flow for creating one Temple product video.

It does not define UI graphics, wireframes, code, APIs, or technical implementation.

## UX Principles

1. The user should always know what step they are in.
2. The user should not need to understand AI providers, folders, metadata, or technical model names.
3. The main action should be obvious at every step.
4. Draft work should be recoverable.
5. Regeneration should be local to the weak part whenever possible.
6. Final export should be clearly separate from draft preview.

## Primary Flow

### Step 1: Enter Temple Product Video Generator

User intent:

Start or continue a product video.

User sees:

- Start New Product Video
- Continue recent draft
- Product Library
- Previous exports

Primary action:

Start New Product Video.

Expected next screen:

Create Video.

### Step 2: Select or Create Product

User intent:

Tell the app which product is being promoted.

User sees:

- Existing products
- Create new product option
- Product name
- Product category
- Product image
- Short product description

Primary action:

Select product or create product.

Expected next screen:

Create Video or Product Detail if the product needs editing.

### Step 3: Provide Materials

User intent:

Give the app enough visual material to make the product recognizable.

User sees:

- Main product image
- Additional materials
- Material readiness status

Primary action:

Add or confirm at least one product photo.

Expected next screen:

Remain on Create Video until required materials are ready.

### Step 4: Enter Chinese Description

User intent:

Describe the desired video in natural Chinese.

User sees:

- Chinese description input
- Target platform
- Tone
- Video length
- CTA

Primary action:

Enter description and start generation.

Expected next screen:

Generation Progress.

### Step 5: Watch Generation Progress

User intent:

Understand what is happening and wait with confidence.

User sees:

- Current stage
- Completed stages
- Product name
- Target platform
- Cancel or retry options when relevant

Primary action:

Wait, cancel, or retry if a failure occurs.

Expected next screen:

Preview when generation succeeds.

### Step 6: Review Preview

User intent:

Decide whether the generated draft is usable.

User sees:

- Video preview
- Scene list
- Narration
- Subtitles
- Caption
- Thumbnail suggestion
- Review status

Primary action:

Approve, edit text, regenerate one scene, reject, or save draft.

Expected next screen:

Export if approved, Scene Detail if revising one scene.

### Step 7: Regenerate One Scene

User intent:

Fix only the weak part.

User sees:

- Selected scene
- Current scene content
- Regeneration note field
- Previous version when available

Primary action:

Regenerate this scene.

Expected next screen:

Generation Progress, then Preview.

### Step 8: Export

User intent:

Create final deliverable for manual posting.

User sees:

- Approved preview
- Platform
- Final MP4 name
- Subtitle option
- Caption
- Metadata summary
- Export status

Primary action:

Export MP4.

Expected result:

Final video package is ready.

## Secondary UX Flows

### Edit Product

The user can edit product information before generation or from Product Detail.

Edited fields should affect future video drafts, not silently alter already approved exports.

### Cancel Generation

Canceling generation should save the current draft state.

The user should understand that generated results may be incomplete.

### Retry Failed Generation

When generation fails, the app should explain:

- What failed
- What was preserved
- What can be retried
- Whether user action is needed

Retry should resume from the nearest useful step.

### Resume Unfinished Work

The user can resume from Home or Previous Projects.

The app should show the last completed step and the next recommended action.

## UX State Definitions

### Draft

Work exists but has not been approved.

### Needs Revision

Preview exists, but at least one part requires changes.

### Approved

User has accepted the preview and content package.

### Exported

Final MP4 and supporting files are available.

### Failed

A generation or export step failed, but recoverable data is preserved.

## Definition of Done

UX Flow V1 is complete when:

1. The primary flow from launch to MP4 export is clear.
2. Secondary flows are defined.
3. Recovery behavior is understandable.
4. Screen-to-screen movement aligns with `APP_BLUEPRINT_V1.md`.
5. User-facing terminology aligns with `USER_JOURNEY_V1.md`.
6. No UI graphics, code, APIs, or implementation details are introduced.
