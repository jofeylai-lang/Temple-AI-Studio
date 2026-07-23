# Temple Product Video Generator V1

Temple Product Video Generator is the first runnable product built on Temple AI Studio.

V1 is local-first. It does not call paid APIs, does not require GitHub CLI, and can still produce a usable 9:16 MP4 when ComfyUI, Whisper, or TTS are not connected.

## Launch

Double-click:

```text
start.bat
```

Or run:

```powershell
cd "D:\AI\Jofey AI Studio\apps\temple-product-video-generator"
python server.py
```

Open:

```text
http://127.0.0.1:4173
```

## One Command Validation

```powershell
cd "D:\AI\Jofey AI Studio\apps\temple-product-video-generator"
python server.py --smoke-test
```

The smoke test creates a demo product, creates a video project, regenerates one scene, approves the project, exports MP4, and verifies the required output package files.

## Local Dependencies

Required:

- Python 3
- Pillow
- FFmpeg

Detected FFmpeg during V1 validation:

```text
C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe
```

If FFmpeg is not found, V1 will still save products, photos, scripts, scenes, subtitles, prompts, and metadata, but it cannot honestly export MP4.

Optional:

- ComfyUI
- Whisper
- Local TTS

## ComfyUI

ComfyUI is optional for V1.

Use Settings to configure:

- ComfyUI URL
- Workflow name or path

If ComfyUI is unavailable, V1 uses the reliable fallback path:

```text
real product photos + scene frames + Ken Burns motion + subtitles + FFmpeg MP4
```

## Workflow

1. Open Product Library.
2. Create or select a product.
3. Upload one or more real product photos.
4. Open Create Video.
5. Enter the Traditional Chinese video request.
6. Generate script, scenes, preview video, subtitles, caption, prompts, and metadata.
7. Open Preview.
8. Review the video and scene list.
9. Open Scene Detail if one scene needs editing or regeneration.
10. Approve the project.
11. Export the complete content package.

## Output Package

Each completed project exports:

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

Default output location:

```text
apps/temple-product-video-generator/data/exports/<project-id>/
```

## Data Location

Default data location:

```text
apps/temple-product-video-generator/data/
```

The data folder contains local products, projects, uploaded images, generated preview files, and exports. It is ignored by Git to avoid committing private materials or generated media.

## Common Errors

### FFmpeg Not Found

Set the FFmpeg path in Settings.

V1 validation found an existing FFmpeg at:

```text
C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe
```

### ComfyUI Not Connected

This is not a V1 blocker. The app will show the connection status and continue using the local fallback generator.

### No Product Photo

Upload at least one product photo before creating a video.

### MP4 Export Failed

Open Generation Progress to read the user-facing error, then retry preview render or export.

## Notes

- User-facing copy defaults to Traditional Chinese and Taiwan usage.
- V1 does not perform voice cloning.
- V1 does not call paid cloud APIs.
- V1 burns subtitles into scene frames and also exports `subtitles.srt`.
