from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from temple_ai_studio.final_activation_recovery import (
    FinalActivationBackupManager,
    RESTORE_CONFIRMATION,
)


class FinalActivationRecoveryTests(unittest.TestCase):
    def test_backup_and_staged_restore_preserve_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "production"
            voice = root / "emma" / "video-activation" / "canonical-video-v1" / "voice" / "segments" / "ref.wav"
            voice.parent.mkdir(parents=True)
            with wave.open(str(voice), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(b"\x01\x00" * 24000)
            profile = root / "emma" / "voice-profiles" / "emma-canonical-video-voice-v1.json"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                json.dumps(
                    {
                        "profileId": "emma-canonical-video-voice-v1",
                        "canonical": True,
                        "referenceAudio": str(voice),
                    }
                ),
                encoding="utf-8",
            )
            adapter = root / "emma" / "identity-adapters" / "identity.json"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("{}", encoding="utf-8")
            version = root / "emma" / "versions" / "emma-production-v1.json"
            version.parent.mkdir(parents=True)
            version.write_text(
                json.dumps({"identityArtifact": str(adapter)}),
                encoding="utf-8",
            )
            state = root / "emma" / "emma-production-state.json"
            state.write_text(
                json.dumps(
                    {
                        "status": "ACTIVE",
                        "activeVersion": "emma-production-v1",
                        "identityActivated": True,
                        "voiceActivated": True,
                    }
                ),
                encoding="utf-8",
            )
            manager = FinalActivationBackupManager(root)
            backup = manager.create("unit")
            restored = manager.restore(
                backup["archive"],
                Path(temporary) / "restored",
                RESTORE_CONFIRMATION,
            )
            self.assertEqual(restored["overall"], "PASS")
            self.assertTrue(
                all(item["ok"] for item in restored["validation"]["checks"])
            )


if __name__ == "__main__":
    unittest.main()
