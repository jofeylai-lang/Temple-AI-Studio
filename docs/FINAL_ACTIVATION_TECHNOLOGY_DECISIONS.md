# Final Activation Technology Decisions

Date: 2026-07-24

Purpose: record the current production selections used by the implemented activation layer.

## Emma Identity

Primary training preparation:

- FLUX.2 Klein 4B Base LoRA with the official Diffusers Klein training script
- FLUX.2 Klein 4B distilled inference
- Qwen Image Edit 2509 immediate multi-reference inference
- OpenCV YuNet and SFace identity evaluation

Reason:

- FLUX.2 Klein 4B and Base are Apache 2.0, support local use and provide a training-to-inference path.
- Qwen Image Edit provides an already usable Apache 2.0 identity-aware edit path through the existing ComfyUI installation.
- SFace provides a local, reproducible identity score instead of visual-only approval.

Rejected as the permanent primary path:

- research-only or noncommercial identity adapters
- prompt-only identity
- unmeasured face similarity

Official references:

- https://github.com/black-forest-labs/flux2
- https://docs.comfy.org/tutorials/flux/flux-2-klein
- https://github.com/huggingface/diffusers/blob/main/examples/dreambooth/README_flux2.md
- https://github.com/QwenLM/Qwen-Image
- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet

## Emma Voice

Primary:

- Qwen3-TTS 12Hz 0.6B Base
- WavLM Base Plus SV speaker verification

Reason:

- Qwen3-TTS supports Chinese, local zero-shot voice cloning and a future fine-tuning path under Apache 2.0.
- The 0.6B model is the conservative first target for the installed 16GB GPU.
- WavLM speaker verification provides a repeatable voice-consistency measure.

Official references:

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/microsoft/wavlm-base-plus-sv

## Video

Current production local path:

- Wan 2.2 TI2V 5B through ComfyUI

Current alternate path:

- LTX 2.3 through ComfyUI, blocked until its installed workflow and commercial license declaration pass

Reason:

- Wan 2.2 TI2V 5B, VAE and text encoder already exist on the production machine.
- The official Wan 2.2 TI2V 5B model is Apache 2.0.
- Its production descriptor has explicit prompt, negative prompt, seed, dimensions, frame count, frame rate, source frame and output bindings.

Measured local benchmark:

- Hardware: NVIDIA GeForce RTX 5080 16GB
- Output: 480 x 832, 16 fps, 33 frames, 2.06 seconds
- End-to-end ComfyUI time: 25 minutes 26 seconds
- Sampling time: 10 minutes 54 seconds
- VAE decode time: 14 minutes 15 seconds
- Peak reserved VRAM: 12.09GB
- Playback and 33-frame decode: PASS
- Product silhouette consistency across sampled frames: PASS
- Commercial motion and generated-text quality: NOT YET ACCEPTED

This proves that the local provider and production descriptor work. It does not
count as commercial acceptance because the short benchmark had limited motion
and distorted generated Chinese text. Product wording must be added during the
subtitle/editing stage rather than generated inside source imagery.

Official references:

- https://github.com/Wan-Video/Wan2.2
- https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B

## Lip Sync

Primary activation target:

- MuseTalk 1.5

Fallback benchmark:

- LatentSync 1.5

Reason:

- MuseTalk is designed for local real-time lip sync and its code and model terms permit commercial use.
- LatentSync 1.5 is Apache 2.0 and fits 16GB VRAM; the newer 1.6 model is documented at approximately 18GB and is not the first target for this GPU.

Official references:

- https://github.com/TMElyralab/MuseTalk
- https://github.com/bytedance/LatentSync

## Provider Policy

- Local-first selection is enabled.
- All paid providers are disabled.
- Monthly and per-job limits are TWD 0.
- Emergency billing stop is active.
- Credentials use Windows current-user DPAPI and never enter the Git repository.
- A generic workflow host cannot satisfy a model capability.
- A provider must pass model, descriptor, runtime, license and connection checks before selection.

No paid provider activation is required for the current recommended path.
