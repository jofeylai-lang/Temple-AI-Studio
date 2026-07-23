# Folder Structure V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This folder structure follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `TECH_PLAN_V1.md`

## Purpose

This document defines the intended folder usage for V1.

It does not create folders, rename folders, delete files, or implement architecture.

## Folder Strategy

V1 should reuse the existing repository structure instead of starting over.

Temple AI Studio is the operating system. Temple Product Video Generator should store its work inside the existing studio folders until a future product layer is approved.

## Existing Folders To Reuse

### `docs/`

Purpose:

Product definition, planning, quality, validation, dependency, and review documents.

### `prompts/video-factory/`

Purpose:

Future home for approved video prompt templates and prompt notes.

### `videos/factory/projects/`

Purpose:

Per-project working area for generated product video projects.

Recommended dated pattern:

```text
videos/factory/projects/YYYY/MM/DD/project-id/
```

### `videos/factory/exports/`

Purpose:

Platform-specific final or review exports.

Recommended dated pattern:

```text
videos/factory/exports/platform/YYYY/MM/DD/file.mp4
```

### `images/`

Purpose:

Product reference images, brand images, and reusable image assets.

### `outputs/`

Purpose:

General studio outputs and reports. Temple Product Video Generator should avoid duplicating final video exports here unless a specific reporting need exists.

### `evaluations/`

Purpose:

Quality reviews, validation notes, and acceptance evidence.

### `archive/`

Purpose:

Non-deleted historical items, obsolete experiments, and superseded planning documents after approval.

## Project Folder Content Model

Each product video project should conceptually contain:

- Input materials
- Product brief
- Scene plan
- Narration text
- Subtitle text
- Caption text
- Thumbnail suggestion
- Preview output
- Final export reference
- Metadata
- Review status
- Regeneration notes

This is a folder usage plan only, not an implementation requirement.

## Naming Principles

Recommended naming principles:

- Use clear product video project ids.
- Use dates for project grouping.
- Use platform names consistently.
- Distinguish draft, preview, approved, and exported files.
- Avoid ambiguous names like final-final or test-new.

Recommended status labels:

- draft
- preview
- approved
- exported
- failed

## Do Not Change In Sprint 2

Sprint 2 does not:

- Create new product folders
- Move existing experiments
- Rename existing folders
- Delete duplicate exports
- Archive files
- Change Git tracking rules

## Definition of Done

Folder Structure V1 is complete when:

1. Existing folders are mapped to V1 usage.
2. Project and export folder intentions are clear.
3. No conflicting folder responsibilities remain in Sprint 2 planning.
4. No physical folder changes are required.
