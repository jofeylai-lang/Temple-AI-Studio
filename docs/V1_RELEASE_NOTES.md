# V1 Release Notes

Product: Temple Product Video Generator

Date: 2026-07-23

Release: V1 Local First

## Highlights

- Upgraded Alpha prototype into a local-first runnable V1.
- Added Python local backend.
- Added persistent local product and project storage.
- Added real product photo upload.
- Added Traditional Chinese content generation.
- Added scene planning, narration, subtitles, prompts, caption, SEO keywords, thumbnail suggestion, and metadata.
- Added real MP4 generation through existing local FFmpeg.
- Added preview playback.
- Added scene-level editing, approval, and regeneration.
- Added complete export package.
- Added settings page for local providers and paths.
- Added one-click Windows startup.

## What Works Now

Users can complete this workflow:

```text
Product data + product photos + Chinese request
-> scene planning
-> preview MP4
-> scene review
-> one-scene regeneration
-> project approval
-> final MP4 export
-> complete content package
```

## Output

The export package includes:

- `final_video.mp4`
- `final_video_subtitled.mp4`
- `subtitles.srt`
- `narration.txt`
- `caption.txt`
- `metadata.json`
- `scenes.json`
- `prompts.json`
- `thumbnail_suggestion.txt`
- `materials_used.txt`

## Provider Policy

V1 defaults to:

- Local-first
- No paid APIs
- No automatic model downloads
- No voice cloning
- ComfyUI optional
- Whisper optional
- TTS optional

## Known Limitation

Automated screenshots could not be captured on this machine because Chrome and Edge headless returned exit code `13`.

This does not affect local product usage or MP4 generation.

## Validated Demo

```text
D:\AI\Jofey AI Studio\apps\temple-product-video-generator\data\exports\project-20260724-66ce7705\final_video.mp4
```

## CEO Acceptance Candidate

Temple Product Video Generator V1 is ready for CEO acceptance review.
