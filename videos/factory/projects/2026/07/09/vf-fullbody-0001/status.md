# Full Body Motion Test Status

Project ID: vf-fullbody-0001
Date: 2026-07-09

## Goal

Move beyond face-only animation and test full-body video generation from a reference image.

## Why This Was Needed

The original beach selfie is a close-up portrait. It does not contain the full body, so full-body animation cannot be inferred reliably from the original image alone.

To improve stability, a full-body character reference was generated first, then used as the input for local image-to-video generation.

## Completed

- Created full-body character reference from the original face photo.
- Saved original face reference.
- Installed local image-to-video support using `diffusers` and `accelerate`.
- Downloaded and ran Stable Video Diffusion locally.
- Generated full-body motion test v1.
- Generated full-body motion test v2 with stronger motion and portrait framing.
- Exported Shorts, Instagram, TikTok, and YouTube versions.

## Outputs

### Reference Images

- `references/source-face-reference.jpg`
- `references/full-body-reference.png`

### Local Video Tests

- `outputs/svd-fullbody-test.mp4`
- `outputs/svd-fullbody-test-vertical.mp4`
- `outputs/svd-fullbody-motion-test.mp4`

### Platform Exports

- `videos/factory/exports/shorts/2026/07/09/vf-fullbody-0001-shorts.mp4`
- `videos/factory/exports/shorts/2026/07/09/vf-fullbody-0001-shorts-v2.mp4`
- `videos/factory/exports/instagram/2026/07/09/vf-fullbody-0001-instagram-reels.mp4`
- `videos/factory/exports/instagram/2026/07/09/vf-fullbody-0001-instagram-reels-v2.mp4`
- `videos/factory/exports/tiktok/2026/07/09/vf-fullbody-0001-tiktok.mp4`
- `videos/factory/exports/tiktok/2026/07/09/vf-fullbody-0001-tiktok-v2.mp4`
- `videos/factory/exports/youtube/2026/07/09/vf-fullbody-0001-youtube.mp4`
- `videos/factory/exports/youtube/2026/07/09/vf-fullbody-0001-youtube-v2.mp4`

## Current Quality Notes

Stable Video Diffusion can create natural image-to-video motion, but it is not a pose-control system. It may create subtle movement, camera motion, clothing motion, and body drift, but it is not yet ideal for controlled walking, waving, dancing, or precise hand gestures.

For realistic full-body acting, the next upgrade should be:

- Wan image-to-video with local models
- pose-driven workflow
- OpenPose or skeleton control
- motion reference video
- optional face refinement with LivePortrait

## Next Step

Build a controlled full-body motion workflow:

```text
full-body reference image
↓
motion reference or pose skeleton
↓
Wan / AnimateDiff / pose-control video model
↓
face refinement
↓
platform export
```

