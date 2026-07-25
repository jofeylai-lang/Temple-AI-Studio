# Temple AI Studio 1.1.1

Release status: Production Hotfix

## Highlights

- Fixed the empty product dropdown by adding a clear first-product state, JSON import and direct text-only recovery path.
- Added product metadata fields and reusable image, Logo, video and document materials.
- Added explicit product-video and text-only modes. Text-only generation requires no product and no uploaded photo.
- Replaced blocking project submission with persistent background jobs that return a job ID immediately.
- Added backend-driven progress, stage history, elapsed time, ETA when reliable, provider/model status and operation messages.
- Added idempotent submission, duplicate-click protection, cancellation, manual retry, transient automatic retry and restart recovery.
- Added completed-job output details, preview links, output-folder action and quality/provider summary.
- Added structured database, product API, job, generation and recovery diagnostics.
- Added safe schema migration from database schema 1 to schema 2 and corrupt-database isolation with backup.
- Disabled browser caching for all API state responses so live progress cannot be replaced by stale data.
- Added duration-conflict detection. The duration selected in the interface remains the source of truth.
- Removed the legacy 18-second minimum from script and rendering stages. The generated MP4 now matches the 5–180 second duration selected in the interface, with an automatic media-duration quality gate.

## Validation

- Product workflow hotfix tests: PASS
- Fresh zero-product state: PASS
- Product persistence after refresh/restart: PASS
- Product video with one image: PASS
- Text-only generation with zero products and zero photos: PASS
- Submission response: 410 ms in local production rehearsal
- Idempotency and duplicate submission: PASS
- Live backend progress and persisted stage history: PASS
- Duration conflict recording: PASS
- Requested-versus-rendered MP4 duration: PASS
- MP4 preview generation and playback probe: PASS
- Existing regression suite: PASS

## Compatibility

- Existing schema 1 products and projects are preserved.
- Existing production data stays outside replaceable program files.
- Paid providers remain disabled.
- Emma identity and voice settings are unchanged.

## Known Limits

- Browser automation security blocked automatic selection of a local upload file. The same production upload API and persisted browser state were validated independently.
- ETA is shown only after enough progress data exists to avoid misleading estimates.
- The production launcher uses Temple OS port `8766` because port `8765` can be occupied by Windows networking activity. Product Video Generator remains at `4173`.
