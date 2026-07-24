# AI Capability Research Matrix

Date: 2026-07-24

Status: Initial Current-State Research

Authority:

- `docs/TEMPLE_AI_CONSTITUTION.md`
- `docs/AI_CAPABILITY_RESEARCH_AND_BENCHMARK_FRAMEWORK_V1.md`

## Purpose

Record current research candidates for every major Temple AI Studio capability.

This matrix does not approve replacement.

## Research Sources

### LLM

- llama.cpp: https://github.com/ggml-org/llama.cpp
- Ollama: https://github.com/ollama/ollama
- Hugging Face Transformers generation docs: https://huggingface.co/docs/transformers/main_classes/text_generation
- OpenAI model API reference: https://platform.openai.com/docs/api-reference/models

Research summary:

Local LLM options are mature enough to benchmark for privacy, cost and offline execution. Cloud LLMs remain strong candidates for quality and reasoning, but paid usage requires CEO approval.

### Image Generation

- ComfyUI docs: https://docs.comfy.org/
- ComfyUI GitHub: https://github.com/comfy-org/ComfyUI
- ComfyUI image-to-image workflow: https://docs.comfy.org/tutorials/basic/image-to-image
- FLUX Kontext docs: https://docs.bfl.ml/kontext/kontext_overview
- Stable Diffusion WebUI Forge: https://github.com/lllyasviel/stable-diffusion-webui-forge

Research summary:

ComfyUI remains the primary local visual workflow engine to benchmark. FLUX-style in-context editing and character consistency are important benchmarks for image editing and identity preservation. Paid image APIs must be compared only after local baselines are measured.

### Video Generation

- Wan2.1: https://github.com/Wan-Video/Wan2.1
- LTX Video docs: https://docs.ltx.io/open-source-model/getting-started/quick-start
- ComfyUI LTX workflow docs: https://docs.comfy.org/tutorials/video/ltxv
- ComfyUI-LTXVideo: https://github.com/Lightricks/ComfyUI-LTXVideo

Research summary:

Open/local video options now include LTX and Wan families. V1's FFmpeg motion assembly is a stable baseline but not a final video-generation capability. Benchmark must compare quality, VRAM, speed and temporal consistency before replacement.

### Talking Head And Lip Sync

- LivePortrait: https://github.com/KlingAIResearch/LivePortrait
- MuseTalk: https://github.com/TMElyralab/MuseTalk
- SadTalker: https://github.com/OpenTalker/SadTalker

Research summary:

LivePortrait is relevant for portrait animation and motion transfer. MuseTalk is relevant for audio-driven lip sync and virtual human workflows. SadTalker remains a talking-face baseline. Emma consistency must dominate raw lip-sync quality.

### Voice Cloning And TTS

- GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS
- GPT-SoVITS changelog: https://github.com/RVC-Boss/GPT-SoVITS/blob/main/docs/en/Changelog_EN.md
- OpenVoice: https://github.com/myshell-ai/OpenVoice
- Coqui TTS: https://github.com/coqui-ai/TTS
- Piper: https://github.com/rhasspy/piper
- Whisper: https://github.com/openai/whisper

Research summary:

GPT-SoVITS is a serious candidate for local voice identity, with ongoing improvements. OpenVoice is relevant for instant voice cloning. Coqui TTS and Piper-style local TTS are candidates for generic narration, but Piper's original repository is archived and needs maintenance risk evaluation. Whisper remains the first local ASR/subtitle alignment benchmark.

### Editing And Automation

- FFmpeg docs: https://ffmpeg.org/documentation.html
- FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
- MoviePy: https://github.com/Zulko/moviepy
- Remotion: https://www.remotion.dev/
- Manim: https://docs.manim.community/

Research summary:

FFmpeg remains the most mature local editing and validation baseline. MoviePy is convenient but may be slower. Remotion is powerful for programmatic video apps but may introduce licensing/cost considerations depending usage. Manim is suitable for programmatic explainer segments, not general product video editing.

### Music

Current research incomplete.

Music must be evaluated for licensing safety before generation quality.

Priority candidates:

- local royalty-free library
- free licensed music sources
- open music generation models
- paid licensed music or generation services

## Capability Candidate Matrix

| Capability | Current | Better Local | Free Service | Paid Service | Replacement Status |
| --- | --- | --- | --- | --- | --- |
| LLM | Codex/OpenAI-assisted + rules | llama.cpp, Ollama, Transformers | reputable free model endpoints | OpenAI, Anthropic, Gemini | Not eligible; benchmark first |
| Image Generation | uploaded photos/placeholders | ComfyUI, FLUX local/dev, Forge | reputable free tiers | OpenAI Images, FLUX API, Imagen | Not eligible; benchmark first |
| Identity Preservation | governance only | embedding checks, reference workflows | open-source embeddings | paid vision APIs | Not eligible; source/gate needed |
| Character Training | none | LoRA/DreamBooth/GPT-SoVITS | free notebooks if privacy-safe | paid character/voice training | Blocked by Emma source material |
| Video Generation | FFmpeg motion assembly | LTX, Wan2.1, ComfyUI video workflows | reputable free tiers | Runway, Kling, Luma, Pika | Not eligible; benchmark first |
| Talking Head | none | LivePortrait, SadTalker, MuseTalk | open demos if privacy-safe | paid avatar APIs | Not eligible; benchmark first |
| Full Body Animation | none | pose-guided ComfyUI/video workflows | open motion tools | paid human motion platforms | Not eligible; benchmark first |
| Lip Sync | none | MuseTalk, Wav2Lip, SadTalker | open demos if privacy-safe | paid lip-sync APIs | Not eligible; benchmark first |
| Voice Cloning | none | GPT-SoVITS, OpenVoice, Coqui XTTS | open demos if privacy-safe | ElevenLabs, OpenAI audio, commercial APIs | Not eligible; benchmark first |
| TTS | text narration file | Piper, Coqui, GPT-SoVITS inference | free TTS if privacy-safe | OpenAI TTS, ElevenLabs, Google TTS | Not eligible; benchmark first |
| Subtitle | timeline SRT | Whisper, WhisperX, faster-whisper | free transcription if privacy-safe | OpenAI transcription, Google STT | Improve current possible |
| Editing | FFmpeg | FFmpeg advanced, MoviePy, Remotion | none preferred | cloud rendering | Keep current until limit proven |
| Music | none | local licensed library/open models | free licensed music | licensed music/generation APIs | Research needed |
| Automation | V1 local workflow | Python orchestrator, ComfyUI API, self-hosted n8n | self-hosted OSS | managed workflow tools | Improve current |

## Immediate Benchmark Order

1. Editing baseline: FFmpeg export and subtitle render.
2. Subtitle baseline: timeline SRT vs Whisper/faster-whisper alignment.
3. Image generation: ComfyUI local workflow baseline.
4. Video generation: LTX/Wan local feasibility.
5. Talking head/lip sync: LivePortrait vs MuseTalk baseline.
6. Voice: GPT-SoVITS/OpenVoice/Coqui feasibility.
7. Identity preservation: Emma source-material-dependent.

## Replacement Conclusions

No replacement is approved by this matrix.

The current decision is:

```text
Build benchmarks first.
```
