# Temple Product Video Generator Alpha

This is the first runnable prototype for Temple Product Video Generator.

It is a zero-install static application shell based on the approved V1 documentation.

## Launch

From this folder:

```powershell
python -m http.server 4173
```

Then open:

```text
http://127.0.0.1:4173
```

Demo state:

```text
http://127.0.0.1:4173/?demo=generated#preview
```

## Included Modules

- Home
- Product Library
- Create Video
- Generation Progress
- Preview
- Scene Detail
- Export

## Current Scope

The Alpha prototype provides real navigation, browser-local state, input validation, placeholder scene generation, scene-level regeneration, preview approval, and export package preparation.

AI engines are not connected yet.

Prepared provider slots:

- Local ComfyUI
- Local Whisper
- FFmpeg
- Future Cloud Provider

## Source Documents

This prototype follows:

- `docs/PRODUCT_SPEC_V1.md`
- `docs/USER_JOURNEY_V1.md`
- `docs/CONTENT_MODEL_V1.md`
- `docs/AI_REASONING_PIPELINE_V1.md`
- `docs/APP_BLUEPRINT_V1.md`
- `docs/VALIDATION_RULES_V1.md`
- `docs/TECH_PLAN_V1.md`
- `docs/DATA_MODEL_V1.md`
