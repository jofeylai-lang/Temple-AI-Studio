# Architecture Plan V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This architecture plan follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `DATA_MODEL_V1.md`
- `WORKFLOW_SPEC_V1.md`
- `TECH_PLAN_V1.md`
- `FOLDER_STRUCTURE_V1.md`
- `DEPENDENCY_MAP_V1.md`

## Purpose

This document defines the planning-level architecture for V1.

It does not define code, APIs, database schemas, deployment, or implementation details.

## Architecture Principle

Temple AI Studio is the operating system.

Temple Product Video Generator is the first application.

The application should depend on shared studio capabilities only where V1 needs them.

## Planning-Level Components

### Product Workspace

Responsibility:

Hold product identity, product materials, draft status, and project references.

### Reasoning Layer

Responsibility:

Convert Chinese request and product information into story plan, scene plan, prompt directions, caption, thumbnail suggestion, and metadata.

### Prompt Layer

Responsibility:

Organize prompt categories and preserve prompt traceability.

### Generation Layer

Responsibility:

Use approved local, cloud, or hybrid generation path to prepare preview media.

V1 does not require all providers.

### Review Layer

Responsibility:

Apply quality checklist, validation rules, and user approval.

### Export Layer

Responsibility:

Prepare final MP4 package, caption, subtitles, metadata, and output location.

### Recovery Layer

Responsibility:

Preserve draft state and resume from the nearest useful step after cancellation or failure.

## Architecture Boundaries

In V1:

- One product video workflow is supported.
- Manual posting is required.
- Human review is required before export.
- Scene-level regeneration is supported.
- Metadata is required.

Not in V1:

- User account architecture
- Billing architecture
- Publishing platform integrations
- Universal provider system
- Advanced timeline editor
- Voice cloning pipeline
- Full-body human animation pipeline

## Definition of Done

Architecture Plan V1 is complete when components, responsibilities, boundaries, and dependency direction are clear without defining implementation details.

