# Workflow Spec V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This workflow spec follows:

- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `UX_FLOW_V1.md`
- `DATA_MODEL_V1.md`

## Purpose

This document defines the canonical V1 workflow.

It does not define code, APIs, UI graphics, or implementation.

## Workflow Stages

### 1. Start Project

Input:

- New video intent or resumed draft.

Output:

- Draft Video Project.

Exit criteria:

- Project has an identity and Draft status.

### 2. Product Selection

Input:

- Existing Product or new Product details.

Output:

- Product linked to Video Project.

Exit criteria:

- Product name, description, category, selling point, and main image are available.

### 3. Creative Brief

Input:

- Chinese description
- Target platform
- Tone
- Length
- CTA

Output:

- Generation-ready brief.

Exit criteria:

- Required inputs pass validation.

### 4. Reasoning Pipeline

Input:

- Product
- Product materials
- Creative brief
- Source of truth documents

Output:

- Intent analysis
- Story plan
- Scene plan
- Prompt directions
- Caption direction
- Thumbnail suggestion

Exit criteria:

- Scene list and content package exist.

### 5. Preview Generation

Input:

- Scene plan
- Prompt directions
- Narration
- Subtitles
- Visual direction

Output:

- Reviewable preview when generation succeeds.

Exit criteria:

- Preview exists or failure recovery path is available.

### 6. Review

Input:

- Preview
- Scene list
- Narration
- Subtitles
- Caption
- Thumbnail suggestion
- Metadata summary

Output:

- Approved, Needs Revision, or Failed status.

Exit criteria:

- User chooses approve, revise, reject, or save draft.

### 7. Single-Scene Regeneration

Input:

- Selected scene
- User revision note

Output:

- Updated scene version.

Exit criteria:

- User keeps new version or restores previous version.

### 8. Export

Input:

- Approved preview
- Caption
- Subtitle choice
- Metadata
- Target platform

Output:

- Final MP4 export package.

Exit criteria:

- Export status is Exported or Failed with recovery path.

## Definition of Done

Workflow Spec V1 is complete when every stage has input, output, and exit criteria, and the workflow supports draft, revision, approval, export, and recovery.

