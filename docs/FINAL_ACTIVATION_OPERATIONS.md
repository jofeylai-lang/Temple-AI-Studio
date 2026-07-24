# Final Activation Operations

Status: implemented, external production assets pending

## Production Root

```text
D:\AI\Temple AI Studio Production Data
```

This root is outside the source repository. Emma media, model files, credentials, logs, generated content and acceptance evidence must not be committed to Git.

## Commands

Initialize production paths:

```powershell
python scripts\run_final_activation.py init
```

Check Emma and provider state:

```powershell
python scripts\run_final_activation.py status
python scripts\run_final_activation.py provider-health
python scripts\run_final_activation.py production-preflight
```

Validate and prepare Emma:

```powershell
python scripts\run_final_activation.py scan-emma
python scripts\run_final_activation.py prepare-emma
```

Store a cloud credential using Windows current-user DPAPI:

```powershell
python scripts\run_final_activation.py store-provider-secret <provider-id>
```

Paid providers remain disabled unless the CEO supplies an approval reference and nonzero per-job and monthly TWD limits:

```powershell
python scripts\run_final_activation.py authorize-billing `
  --approval-reference <CEO-approval-id> `
  --monthly-limit-twd <amount> `
  --per-job-limit-twd <amount>
```

Immediately disable all billing providers:

```powershell
python scripts\run_final_activation.py emergency-stop-billing
```

Run a strict real-production project:

```powershell
python scripts\run_final_activation.py run-production --request <request.json>
```

The production command refuses to run if Emma identity, Emma voice, video, voice, lip sync, rendering or commercial-quality validation is unavailable. It never substitutes mock, simulator, demo or PIL output.

Run commercial acceptance after seven real scenario manifests exist:

```powershell
python scripts\run_final_activation.py acceptance
```

Create a final release only after acceptance passes:

```powershell
python scripts\run_final_activation.py release --version <version>
```

The accepted release contains:

- `install_temple_ai_studio.bat`: user-level production installer
- `start_temple_ai_studio.bat`: starts the OS service and product application, prevents duplicate services and opens the browser
- `stop_temple_ai_studio.bat`: stops only the recorded Temple processes
- `RELEASE_MANIFEST.json`: complete file list and SHA-256 checksums

The installer stages the new program, moves an existing program folder into a timestamped backup, preserves the external data root and creates a desktop shortcut named `啟動 Temple AI Studio`.

The final FFmpeg renderer removes source metadata before export. This prevents
ComfyUI workflow JSON, prompts and other source-container metadata from being
copied into the commercial MP4.

## Local Production Providers

- Qwen Image Edit 2509: real image-edit workflow through ComfyUI
- Wan 2.2 TI2V 5B: real image-to-video workflow through ComfyUI
- Qwen3-TTS 0.6B Base: Emma voice profile and local TTS after runtime installation
- MuseTalk 1.5: primary local lip-sync candidate after runtime installation
- LatentSync 1.5: benchmark fallback after runtime installation
- FFmpeg 7.1: final H.264/AAC rendering and Traditional Chinese subtitle burn-in
- OpenCV YuNet/SFace: Emma face verification after evaluator model installation
- WavLM Base Plus SV: Emma voice verification after evaluator model installation

Generic ComfyUI is a workflow host only. It cannot be selected as an image, video or lip-sync provider without a production-approved workflow descriptor.

## Research Evidence

When `researchRequired` is false, the stage is recorded as not required.

When it is true, `researchEvidence` must point to a JSON file with:

- `provenance: real-production`
- a known production `providerId`
- at least one source
- title, source location and finding for every source

The workflow blocks rather than marking unperformed research as complete.

## Release Gate

The final commercial release remains locked until:

- Emma identity and voice are activated
- all mandatory provider health checks pass
- seven representative real commercial scenarios pass
- every output MP4 is playable
- all quality thresholds pass
- no accepted stage uses mock or simulator provenance
