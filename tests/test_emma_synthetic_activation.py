from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from temple_ai_studio.emma_synthetic_activation import (
    EmmaSyntheticActivation,
    TARGET_DISTRIBUTION,
    flux2_graph,
)
from temple_ai_studio.provider_activation import ProviderActivationManager


class EmmaSyntheticActivationTests(unittest.TestCase):
    def make_seed_package(self, root: Path) -> Path:
        seed = root / "seed"
        manifest_dir = seed / "07_manifests"
        anchor_dir = seed / "01_identity_anchors"
        manifest_dir.mkdir(parents=True)
        anchor_dir.mkdir(parents=True)
        files = []
        for index in range(3):
            path = anchor_dir / f"anchor-{index + 1}.png"
            Image.new("RGB", (800, 1200), (180 + index, 120, 80)).save(path)
            files.append(
                {
                    "file": f"01_identity_anchors/{path.name}",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "width": 800,
                    "height": 1200,
                    "category": "01_identity_anchors",
                }
            )
        manifest = {
            "character": {
                "type": "fully_synthetic_ai_character",
                "adult_character": True,
            },
            "files": files,
        }
        (manifest_dir / "emma_identity_manifest_v1.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        (manifest_dir / "emma_profile_v1.json").write_text("{}", encoding="utf-8")
        return seed

    def test_seed_validation_and_generation_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            activation = EmmaSyntheticActivation(
                root / "project",
                root / "production",
                self.make_seed_package(root),
            )
            report = activation.validate_seed_package()
            plan = activation.build_plan()
            self.assertEqual(report["overall"], "PASS")
            self.assertEqual(plan["target"], 80)
            self.assertEqual(plan["distribution"], TARGET_DISTRIBUTION)
            self.assertEqual(len({item["seed"] for item in plan["items"]}), 80)
            self.assertEqual(
                {item["anchorIndex"] for item in plan["items"]},
                {1, 2, 3},
            )

    def test_flux2_reference_graph_has_no_paid_api_node(self) -> None:
        graph = flux2_graph("flux-2-klein-4b.safetensors", 4, 1.0)
        self.assertEqual(graph["4"]["inputs"]["unet_name"], "flux-2-klein-4b.safetensors")
        self.assertEqual(graph["10"]["class_type"], "ReferenceLatent")
        self.assertEqual(graph["11"]["class_type"], "ReferenceLatent")
        self.assertFalse(
            any("api" in node["class_type"].lower() for node in graph.values())
        )

    def test_local_stack_keeps_paid_providers_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProviderActivationManager(Path(temporary) / "providers")
            defaults = manager.defaults()
            self.assertFalse(defaults["billing"]["enabled"])
            self.assertEqual(defaults["billing"]["monthlyLimitTwd"], 0.0)
            self.assertEqual(defaults["billing"]["perJobLimitTwd"], 0.0)
            paid = [item for item in defaults["providers"] if item.get("paid")]
            self.assertTrue(paid)
            self.assertTrue(all(item["enabled"] is False for item in paid))
            provider_ids = {item["id"] for item in defaults["providers"]}
            self.assertIn("qwen3-voice-design-local", provider_ids)
            self.assertIn("emma-quality-local", provider_ids)


if __name__ == "__main__":
    unittest.main()
