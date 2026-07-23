# Technical Plan V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This technical plan follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`
- `PROMPT_SYSTEM_V1.md`
- `QUALITY_CHECKLIST_V1.md`

## Purpose

This document defines technical planning boundaries for V1.

It does not define code, APIs, database schemas, UI implementation, or feature implementation.

## V1 Technical Direction

Temple AI Studio remains the operating system.

Temple Product Video Generator is the first application.

V1 should validate one repeatable workflow:

```text
Product information + product photo + Chinese description
-> story plan
-> scene plan
-> narration/subtitles/caption
-> preview
-> review
-> vertical MP4 export package
```

## Technical Scope

In scope for planning:

- Product draft lifecycle
- Product material handling
- Scene-level content model
- Prompt category governance
- Metadata requirements
- Review status model
- Export package definition
- Recovery behavior
- Local/cloud model decision rules

Out of scope for V1:

- Universal AI engine
- All provider integrations
- Automatic social publishing
- User accounts
- Billing
- API design
- Code implementation
- Advanced video editor timeline
- Voice cloning
- Full-body human animation

## Generation Strategy

V1 should use a hybrid-ready strategy:

- Local preparation for product understanding, planning, prompts, captions, subtitles, metadata, and review.
- Local or cloud generation only when the chosen path is approved.
- Cloud generation may be used for higher-quality media when local quality is insufficient and the user has approved account/credit usage.

This keeps V1 aligned with `NEW_ROADMAP.md`: build one useful product before expanding providers.

## Core Planning Objects

The product should conceptually track:

- Product
- Product material
- Video project
- Scene
- Prompt category output
- Preview
- Export package
- Review status
- Recovery state

These are planning objects only, not implementation schemas.

## Status Model

Allowed statuses:

- Draft
- Needs Revision
- Approved
- Exported
- Failed
- Archived candidate

Only Draft, Needs Revision, Approved, Exported, and Failed are active V1 workflow states.

Archived candidate is a project lifecycle label for later governance, not a user-facing V1 action.

## Technical Risks

### Media Growth

Generated videos and images can grow quickly.

Planning response:

Define final exports, drafts, and reference materials separately in folder guidance.

### Provider Drift

Different providers may produce inconsistent outputs.

Planning response:

Use one approved generation path for V1 and keep provider abstraction minimal.

### Prompt Drift

Successful prompts can become scattered.

Planning response:

Use prompt categories and version references from `PROMPT_SYSTEM_V1.md`.

### Quality Gaps

Local video quality may not meet business expectations.

Planning response:

Use quality gates and allow cloud path selection only with approval.

### Recovery Gaps

Generation may fail midway.

Planning response:

Preserve draft state and resume from the nearest useful step.

## Definition of Done

Technical Plan V1 is complete when:

1. V1 scope is technically bounded.
2. Planning objects are identified.
3. Status model aligns with user journey and app blueprint.
4. Generation strategy is consistent with roadmap.
5. Risks are documented.
6. No code, APIs, database schema, or implementation details are defined.
