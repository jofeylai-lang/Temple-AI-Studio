# Emma Production Intake

Status: operational specification

This document describes the files required by the implemented Emma production intake validator.

## Ready Paths

```text
D:\AI\Temple AI Studio Production Data\emma\intake\identity
D:\AI\Temple AI Studio Production Data\emma\intake\voice
D:\AI\Temple AI Studio Production Data\emma\intake\consent
D:\AI\Temple AI Studio Production Data\emma\intake\emma-intake.json
D:\AI\Temple AI Studio Production Data\emma\intake\consent\emma-consent.json
```

The intake process does not modify the original files. Accepted files are copied into a versioned production dataset. Rejected files remain traceable in the intake report.

## Identity Images

Minimum accepted set: 20 images.

Recommended accepted set: 50 images.

Minimum coverage:

- face: 5
- half-body: 4
- full-body: 4
- profile, expression and pose combined: 5

File requirements:

- JPEG, PNG or WebP
- both dimensions at least 768 pixels
- 1024 pixels or higher preferred; original camera files are best
- one authorized adult subject
- sharp eyes and face
- varied front, three-quarter and profile angles
- varied neutral and natural expressions
- varied half-body and full-body poses
- normal clothing with visible body proportions
- no beauty filter, face reshaping, watermark or heavy compression

The validator rejects missing files, unsupported types, insufficient resolution, poor exposure, low contrast, weak detail, exact duplicates and near duplicates.

## Voice Audio

Minimum accepted duration: 600 seconds.

Recommended accepted duration: 1,800 seconds.

File requirements:

- mono PCM WAV
- 24,000 to 48,000 Hz
- 16, 24 or 32-bit PCM
- each clip 3 to 30 seconds
- one speaker
- quiet room
- no music, reverb, aggressive denoising or clipping
- an exact Traditional Chinese transcript for every clip

The validator rejects unsupported encoding, missing transcripts, excessive silence, clipping, insufficient level and duplicate audio.

## Consent

Complete `emma-consent.json` and place the signed evidence file in the same `consent` folder.

Required fields:

- `subjectLegalName`
- `rightsHolder`
- `consentGranted: true`
- `sourceOwnershipConfirmed: true`
- permitted uses: identity training, voice cloning, synthetic media and commercial content
- `territory`
- `term`
- `signedAt`
- `revocationContact`
- `evidenceFile`

The signed evidence can be PDF, JPEG or PNG. Production activation remains blocked until every consent check passes.

## Intake Manifest

List every file in `emma-intake.json`.

Identity entry example:

```json
{
  "file": "identity/emma-face-001.jpg",
  "kind": "face",
  "notes": "front, neutral expression"
}
```

Voice entry example:

```json
{
  "file": "voice/emma-voice-001.wav",
  "transcript": "這是與錄音完全一致的逐字稿。"
}
```

## Validation Commands

```powershell
python scripts\run_final_activation.py scan-emma
python scripts\run_final_activation.py prepare-emma
```

`prepare-emma` copies only accepted assets and creates identity-adapter and voice-profile preparation records. It does not silently train or activate an identity.
