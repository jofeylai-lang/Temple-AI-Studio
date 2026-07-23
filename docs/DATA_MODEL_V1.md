# Data Model V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This data model follows:

- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `VALIDATION_RULES_V1.md`

## Purpose

This document defines the conceptual data model for V1.

It does not define database schemas, APIs, code, or implementation details.

## Conceptual Objects

### Product

Represents the item being promoted.

Required fields:

- Product name
- Product category
- Product description
- Main selling point
- Main product image reference

Optional fields:

- Brand notes
- Additional product materials
- Previous video references

### Product Material

Represents user-provided source material.

Required fields:

- Material type
- File reference
- Usage role

Usage roles:

- Main product image
- Additional product photo
- Packaging photo
- Brand image
- Logo
- Reference video

### Video Project

Represents one product video task.

Required fields:

- Project id
- Product reference
- Created date
- Target platform
- Language
- Tone
- Video length target
- Chinese description
- Review status

### Scene

Represents one segment of the product video.

Required fields:

- Scene id
- Scene order
- Purpose
- Estimated duration
- Visual description
- Narration
- Subtitle
- Prompt direction
- Music direction
- Transition direction
- Scene status

### Prompt Record

Represents prompt-related generation guidance.

Required fields:

- Prompt category
- Prompt version
- Product reference
- Scene reference when applicable
- Source document references
- Review status

### Preview

Represents reviewable draft output.

Required fields:

- Preview reference
- Related video project
- Scene version references
- Created date
- Review status

### Export Package

Represents the final deliverable package.

Required fields:

- Final MP4 reference
- Caption reference
- Subtitle reference
- Metadata reference
- Thumbnail suggestion
- Target platform
- Export status

### Metadata

Represents traceability for the generated product video.

Required fields:

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

## Object Relationships

- One Product can have many Product Materials.
- One Product can have many Video Projects.
- One Video Project belongs to one Product.
- One Video Project has many Scenes.
- One Scene can have many Prompt Records over time.
- One Video Project can have many Previews.
- One approved Preview can produce one Export Package.
- One Export Package must have one Metadata record.

## Definition of Done

Data Model V1 is complete when the conceptual objects support product selection, generation, review, single-scene regeneration, export, metadata, and recovery without implementation details.

