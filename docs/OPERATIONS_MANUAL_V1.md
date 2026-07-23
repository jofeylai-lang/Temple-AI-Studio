# Operations Manual V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This operations manual follows:

- `USER_JOURNEY_V1.md`
- `WORKFLOW_SPEC_V1.md`
- `QUALITY_CHECKLIST_V1.md`
- `FOLDER_STRUCTURE_V1.md`
- `RELEASE_CHECKLIST_V1.md`

## Purpose

This document defines how V1 should be operated at a process level.

It does not define code, UI, APIs, or implementation.

## Operating Rhythm

Recommended daily usage:

1. Select product.
2. Confirm product materials.
3. Enter Chinese video description.
4. Generate draft.
5. Review preview.
6. Regenerate weak scene if needed.
7. Approve final preview.
8. Export package.
9. Manually post or archive.

## Human Review Responsibilities

The reviewer checks:

- Product accuracy
- Temple Brand DNA
- Scene quality
- Subtitle readability
- Caption usefulness
- CTA tone
- Export package completeness

## Project Lifecycle

Draft:

Initial work in progress.

Needs Revision:

Review found a problem.

Approved:

Preview accepted.

Exported:

Final package prepared.

Failed:

Generation or export failed and awaits recovery.

Archived Candidate:

No longer active but should not be deleted.

## Recovery Operation

If generation fails:

1. Identify failed stage.
2. Confirm preserved work.
3. Retry from nearest useful step.
4. If retry fails again, save as Failed and document issue.

If export fails:

1. Preserve approved preview.
2. Retry export.
3. If export cannot complete, keep project Approved but not Exported.

## Definition of Done

Operations Manual V1 is complete when the user can understand how to operate the product workflow without implementation details.

