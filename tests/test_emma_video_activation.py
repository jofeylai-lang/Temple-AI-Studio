from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from temple_ai_studio.emma_production import EmmaProductionActivator
from temple_ai_studio.emma_video_activation import text_similarity


class EmmaVideoActivationTests(unittest.TestCase):
    def test_traditional_chinese_transcript_similarity_ignores_punctuation(self) -> None:
        self.assertEqual(text_similarity("大家好，我是 Emma。", "大家好我是 Emma"), 1.0)
        self.assertLess(text_similarity("今天介紹手鍊", "明天介紹香氛"), 0.8)

    def test_prepared_synthetic_video_package_can_activate_without_legacy_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            emma = root / "production" / "emma"
            project.mkdir()
            activator = EmmaProductionActivator(project, emma)
            activator.initialize()
            identity = root / "identity.json"
            voice = root / "voice.json"
            evidence = root / "evidence.json"
            identity.write_text(
                json.dumps({"identityVersion": "emma-synthetic-video-v2"}),
                encoding="utf-8",
            )
            voice.write_text(
                json.dumps(
                    {
                        "profileId": "emma-canonical-video-voice-v1",
                        "referenceAudio": "voice.wav",
                        "referenceText": "大家好",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "provenance": "real-production",
                        "identityEvaluator": "opencv-sface",
                        "voiceEvaluator": "wavlm-base-plus-sv",
                        "checks": {
                            name: {"passed": True}
                            for name in [
                                "identitySimilarity",
                                "bodyConsistency",
                                "voiceSimilarity",
                                "voiceNaturalness",
                                "commercialUsability",
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = activator.activate_prepared_version(
                identity,
                voice,
                evidence,
                {
                    "overall": "PASS",
                    "provenance": "real-production",
                    "schema": "test.preparation.v1",
                },
            )
            self.assertEqual(result["overall"], "PASS")
            self.assertEqual(
                result["state"]["activeVoiceProfile"],
                "emma-canonical-video-voice-v1",
            )
            self.assertEqual(
                result["state"]["activeIdentityVersion"],
                "emma-synthetic-video-v2",
            )
            core_status = activator.core.status()
            self.assertEqual(core_status["status"], "production-active")
            core_profile = json.loads(
                activator.core.profile_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                core_profile["canonicalVoiceProfile"],
                "emma-canonical-video-voice-v1",
            )
            self.assertEqual(
                core_profile["productionActivation"]["productionVersion"],
                result["version"]["version"],
            )
            self.assertEqual(
                core_profile["productionActivation"]["identityVersion"],
                "emma-synthetic-video-v2",
            )
            self.assertEqual(
                core_profile["permanentIdentity"]["faceIdentity"]["status"],
                "synthetic-production-active",
            )
            first_version = result["version"]["version"]
            second_identity = root / "identity-v2.json"
            second_voice = root / "voice-v2.json"
            second_identity.write_text(
                json.dumps({"identityVersion": "emma-synthetic-video-v3"}),
                encoding="utf-8",
            )
            second_voice.write_text(
                json.dumps(
                    {
                        "profileId": "emma-canonical-video-voice-v2",
                        "referenceAudio": "voice-v2.wav",
                        "referenceText": "第二版",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            second = activator.activate_prepared_version(
                second_identity,
                second_voice,
                evidence,
                {
                    "overall": "PASS",
                    "provenance": "real-production",
                    "schema": "test.preparation.v1",
                },
            )
            self.assertNotEqual(second["version"]["version"], first_version)
            rollback = activator.rollback(
                first_version,
                f"ROLLBACK {first_version}",
            )
            self.assertEqual(rollback["overall"], "PASS")
            self.assertEqual(
                rollback["state"]["activeIdentityVersion"],
                "emma-synthetic-video-v2",
            )
            self.assertEqual(
                rollback["state"]["activeVoiceProfile"],
                "emma-canonical-video-voice-v1",
            )
            rolled_back_profile = json.loads(
                activator.core.profile_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                rolled_back_profile["productionActivation"]["productionVersion"],
                first_version,
            )


if __name__ == "__main__":
    unittest.main()
