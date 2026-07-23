# Dependency Map V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This dependency map follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `TECH_PLAN_V1.md`

## Purpose

This document maps dependencies for V1 at a planning level.

It does not define implementation, APIs, installation steps, or code.

## Document Dependencies

### Product Definition

Depends on:

- `PRODUCT_SPEC_V1.md`
- `NEW_ROADMAP.md`

Used by:

- App Blueprint
- UX Flow
- Technical Plan
- Validation Rules

### User Journey

Depends on:

- Product Spec
- Content Model
- App Blueprint

Used by:

- UX Flow
- Quality Checklist
- Validation Rules

### Content Model

Depends on:

- Product Spec
- Temple Brand DNA defined in Content Model
- AI Reasoning Pipeline

Used by:

- Prompt System
- Quality Checklist
- Validation Rules

### AI Reasoning Pipeline

Depends on:

- Product Spec
- Content Model
- User Journey

Used by:

- Prompt System
- Technical Plan
- Quality Checklist

### App Blueprint

Depends on:

- Product Spec
- User Journey
- AI Reasoning Pipeline

Used by:

- UX Flow
- Technical Plan
- Validation Rules

## Product Dependencies

### Required User Inputs

The product depends on:

- Product name
- Product description
- Main selling point
- Target platform
- Product photo
- Chinese video description

### Required Content Outputs

The product depends on:

- Video concept
- Scene plan
- Narration
- Subtitles
- Caption
- Thumbnail suggestion
- Metadata

### Required Review Dependencies

The product depends on:

- Quality checklist
- Review status
- User approval before export

### Required Export Dependencies

The product depends on:

- Approved preview
- Platform target
- Caption
- Subtitle choice
- Metadata
- Final MP4 export location

## External Tool Dependencies

Current project context includes external tools from prior experiments:

- Local ComfyUI environment
- LivePortrait setup
- FFmpeg from Jianying Pro
- Python 3.10 environment
- Hugging Face model cache
- Possible cloud video platforms

V1 planning does not require all of these to be used.

The chosen generation path should be approved before implementation.

## Dependency Risks

### Provider Availability

Risk:

Local or cloud generation may not produce acceptable quality.

Mitigation:

Keep generation path selectable at planning level and require quality checks.

### Cost and Account Access

Risk:

Cloud generation may require login, credits, or manual approval.

Mitigation:

Cloud use remains approval-based.

### Documentation Quality

Risk:

Corrupted Chinese documentation can mislead future work.

Mitigation:

Sprint 2 repaired corrupted V1 journey/content examples and documents remaining risk in review.

### Folder Ambiguity

Risk:

Outputs and experiments may become mixed.

Mitigation:

Follow `FOLDER_STRUCTURE_V1.md`.

## Definition of Done

Dependency Map V1 is complete when:

1. Document dependencies are clear.
2. Product dependencies are clear.
3. Review dependencies are clear.
4. Export dependencies are clear.
5. External dependency risks are documented.
6. No implementation, APIs, or installation steps are defined.
