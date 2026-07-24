# Emma Production Activation Report

Version: 1.1.0

Status: PASS

## Activated Identity

- Identity version: `emma-synthetic-video-v2`
- Character type: fully synthetic adult AI character
- Primary identity anchors: 5
- Existing approved synthetic expansion images: 43
- Approved video-derived reference frames: 12
- Video-derived coverage: close-up, upper body, profile, expression, dynamic composition
- Identity gate: OpenCV YuNet and SFace against at least 3 primary anchors
- Minimum retained three-anchor similarity: 0.47235
- Closed-eye gate: MediaPipe Face Landmarker

## Activated Voice

- Voice profile: `emma-canonical-video-voice-v1`
- Source: CEO-approved synthetic Emma video audio
- Usable canonical segments: 2
- Usable canonical duration: 8.77 seconds
- ASR: Faster-Whisper large-v3-turbo with Silero VAD and word timestamps
- Transcript language: Traditional Chinese (`zh-TW`)
- Voice engine: Qwen3-TTS 12Hz 0.6B Base
- Speaker evaluator: Microsoft WavLM Base Plus SV
- Clone similarity: 0.957712
- Generated-content transcription alignment: 1.0
- Voice naturalness score: 0.906928
- Pitch, accent and speaking style modification: none

## Commercial Acceptance

Seven real local production videos passed:

1. Product introduction
2. Spiritual content
3. Short-form social video
4. Emma presenter
5. Talking head
6. Mixed product and Emma
7. Alternate 16:9 format

Acceptance pass rate: 100%

Paid-provider cost: TWD 0

Automatic repair was exercised on failed voice, lip-sync and rendering attempts. Only failed components were regenerated.

## Recovery

- Final activation backup: PASS
- Staged restore with checksum validation: PASS
- Restored identity artifact: PASS
- Restored canonical reference audio: PASS
- Raw intake, model files, exports and provider secrets are excluded from the activation backup.

## Production Paths

- Production state: `D:\AI\Temple AI Studio Production Data\emma\emma-production-state.json`
- Identity adapter: `D:\AI\Temple AI Studio Production Data\emma\identity-adapters\emma-synthetic-video-v2.json`
- Voice profile: `D:\AI\Temple AI Studio Production Data\emma\voice-profiles\emma-canonical-video-voice-v1.json`
- Activation evidence: `D:\AI\Temple AI Studio Production Data\emma\video-activation\canonical-video-v1`
- Commercial acceptance: `D:\AI\Temple AI Studio Production Data\acceptance`
- Backups: `D:\AI\Temple AI Studio Production Data\backups\final-activation`
