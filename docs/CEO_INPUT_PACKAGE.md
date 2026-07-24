# CEO Input Package

Status: one consolidated external-dependency request

## Decision Requested

Approve the following as one action:

1. Allow network download and user-level installation of the free local components listed below.
2. Keep every paid provider disabled with monthly and per-job limits of TWD 0.
3. Supply the authorized Emma identity, voice and consent materials at the ready paths below.

No administrator privilege or paid API is requested.

## Emma Identity Materials

Place files in:

```text
D:\AI\Temple AI Studio Production Data\emma\intake\identity
```

Minimum accepted quantity: 20.

Recommended accepted quantity: 50.

Because automatic filtering may reject weak or duplicate files, supplying 50 to 60 original images is recommended.

Required coverage:

- at least 5 clear face images
- at least 4 half-body images
- at least 4 full-body images
- at least 5 combined profile, expression and pose images

Specifications:

- JPEG, PNG or WebP
- both dimensions at least 768 pixels; 1024 to 2048 preferred
- original, sharp, evenly exposed
- varied angles, expressions, poses, clothing and backgrounds
- one authorized adult subject
- no beauty filters, face reshaping, watermark or heavy compression

## Emma Voice Materials

Place files in:

```text
D:\AI\Temple AI Studio Production Data\emma\intake\voice
```

Minimum accepted duration: 10 minutes.

Recommended accepted duration: 30 minutes.

Specifications:

- mono PCM WAV
- 24 to 48 kHz
- 16, 24 or 32-bit PCM
- each clip 3 to 30 seconds
- quiet room, one speaker
- no music, reverb, clipping or aggressive denoising
- an exact Traditional Chinese transcript for every clip

List filenames, categories and transcripts in:

```text
D:\AI\Temple AI Studio Production Data\emma\intake\emma-intake.json
```

## Consent And Rights

Complete:

```text
D:\AI\Temple AI Studio Production Data\emma\intake\consent\emma-consent.json
```

Place the signed PDF, JPEG or PNG evidence in the same folder.

Required confirmation:

- subject legal name
- rights holder
- source ownership
- identity training
- voice cloning
- synthetic media
- commercial content
- territory
- term
- signing date
- revocation contact

## Local Downloads And Installation

Approval is requested to download and install these official free local components:

- FLUX.2 Klein 4B distilled and 4B Base for Emma identity inference and LoRA preparation
- Qwen3-TTS 12Hz 0.6B Base and its isolated Python runtime
- MuseTalk 1.5 runtime and model assets
- OpenCV YuNet and SFace evaluator models
- Microsoft WavLM Base Plus SV evaluator model
- local SyncNet and OpenCLIP assets for lip-sync and commercial-quality analysis

Existing ComfyUI, Qwen Image Edit 2509, Wan 2.2 TI2V 5B and FFmpeg will be reused.

Expected direct provider or API cost: TWD 0.

Recommended free disk reservation: 40 GB.

Expected local costs: electricity, GPU time and disk space only.

## Provider Decision

Recommended decision:

- use local Qwen Image Edit for current image production
- use local Wan 2.2 TI2V 5B for current video production
- activate local Qwen3-TTS for Emma voice
- activate local MuseTalk 1.5 for primary lip sync
- keep LatentSync 1.5 as a later local benchmark fallback
- keep OpenAI, Google, Runway and Kling disabled
- do not provide any API key at this stage

This avoids cloud upload of Emma face, voice and product materials.

## Privacy

With the recommended option:

- Emma media remains on this computer
- training and evaluation run locally
- no face, voice or product file is sent to a cloud provider
- no API key is required
- secrets remain protected by Windows current-user DPAPI
- source media, models, logs and generated files remain outside Git

## Approval Reply

After the materials are in place, reply once with:

```text
已核准免費本機模型與工具的網路下載及使用者層級安裝。
維持所有付費 Provider 停用，月額與單次上限皆為 TWD 0。
Emma 素材、逐字稿與同意文件已放入指定資料夾。
```

After this single approval, implementation resumes with intake validation, installation, identity and voice activation, seven real commercial acceptance projects, final packaging, Git commit, push and release tag.
