# V1 Known Limitations

## Non-Blocking Limitations

- ComfyUI is optional and not the default generation path.
- Whisper is optional; V1 uses generated subtitle timing when Whisper is unavailable.
- TTS is optional; V1 can export a silent MP4 with narration text and subtitles.
- Browser headless screenshot capture returns exit code `13` on this machine.
- Application-side evidence screenshots are used instead of browser-rendered screenshots.

## Not In V1 Scope

- Paid cloud generation APIs
- Voice cloning
- Automatic posting to Instagram, TikTok, or YouTube
- Large model downloads
- Full non-template LLM generation

## Current Risk

The app depends on an available FFmpeg binary for honest MP4 export.

Validated FFmpeg path:

```text
C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe
```
