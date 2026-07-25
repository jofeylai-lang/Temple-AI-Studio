# Product Workflow Hotfix Report

Version: 1.1.1
Scope: Product data flow, submission feedback and live progress

## Root Cause

The production database was valid but contained zero products. The interface rendered an empty select without explaining the state or offering a recovery path.

Project submission called the complete script, image and video pipeline synchronously. The browser therefore received no response until generation finished. Project state was too coarse to identify the active stage, and browser caching could return a stale `/api/state` response even after the backend had created a new job.

The original backend also required a stored product and one photo for every workflow, so a zero-photo text-only request could not run.

## Fixes

- Added an explicit zero-product state with create, import and text-only actions.
- Added stable product IDs, duplicate-name support and expanded product/material metadata.
- Added separate product and text-only modes with field-level Traditional Chinese validation.
- Added persistent background jobs with immediate `202` response, idempotency, cancellation, retry and restart recovery.
- Added backend-driven weighted stages from validation through render/export.
- Added stage history, elapsed time, conservative ETA, provider/model status and structured logs.
- Added completed and failed job actions with output path, preview, quality summary, suggested recovery and log access.
- Added schema 2 migration, production database health reporting and corrupt-database backup/recovery.
- Added `Cache-Control: no-store` to APIs and `cache: no-store` to frontend requests.
- Added duration conflict detection with interface duration as the source of truth.
- Corrected the legacy fixed-duration scene allocation and per-scene two-second render floor, then added an MP4 duration quality gate.
- Added a local text-only visual source so zero-photo jobs produce real MP4 previews.

## Production Paths

- Data root: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator`
- Database: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\database.json`
- Uploads: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\uploads`
- Projects: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\projects`
- Exports: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\exports`
- Logs: `D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\logs`

## Evidence

Evidence root:

`D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\evidence\product-hotfix-1.1.1`

The evidence contains browser screenshots, the real job timeline, API latency result and MP4 playback metadata.

## Validation Result

All required hotfix acceptance cases passed. Full case-level results are recorded in `HOTFIX_VALIDATION_1.1.1.json` in the evidence root.

The one-click production launcher was validated at `http://127.0.0.1:4173`. Its local Temple OS health service uses `http://127.0.0.1:8766`.

No Emma model, voice profile, paid-provider setting or production media was changed by this hotfix.
