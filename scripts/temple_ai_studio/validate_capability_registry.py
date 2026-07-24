from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CAPABILITIES = {
    "llm",
    "image-generation",
    "identity-preservation",
    "character-training",
    "video-generation",
    "talking-head",
    "full-body-animation",
    "lip-sync",
    "voice-cloning",
    "tts",
    "subtitle",
    "editing",
    "music",
    "automation",
}

REQUIRED_DIMENSIONS = {
    "quality",
    "stability",
    "maintainability",
    "cost",
    "privacy",
    "localCapability",
    "automationPotential",
    "emmaConsistency",
}

REQUIRED_FIELDS = {
    "id",
    "name",
    "purpose",
    "currentImplementation",
    "currentStatus",
    "currentBenchmarkTarget",
    "localCandidates",
    "freeServiceCandidates",
    "paidServiceCandidates",
    "emmaCritical",
}


def validate(path: Path) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []

    dimensions = set(registry.get("scoringDimensions", []))
    missing_dimensions = sorted(REQUIRED_DIMENSIONS - dimensions)
    if missing_dimensions:
        errors.append(f"Missing scoring dimensions: {', '.join(missing_dimensions)}")

    capabilities = registry.get("capabilities", [])
    capability_ids = [capability.get("id") for capability in capabilities]
    duplicate_ids = sorted({item for item in capability_ids if capability_ids.count(item) > 1})
    if duplicate_ids:
        errors.append(f"Duplicate capability ids: {', '.join(duplicate_ids)}")

    missing_capabilities = sorted(REQUIRED_CAPABILITIES - set(capability_ids))
    if missing_capabilities:
        errors.append(f"Missing required capabilities: {', '.join(missing_capabilities)}")

    for capability in capabilities:
        cap_id = capability.get("id", "<missing-id>")
        missing_fields = sorted(REQUIRED_FIELDS - set(capability.keys()))
        if missing_fields:
            errors.append(f"{cap_id}: missing fields: {', '.join(missing_fields)}")
        for list_field in ["localCandidates", "freeServiceCandidates", "paidServiceCandidates"]:
            if not isinstance(capability.get(list_field), list):
                errors.append(f"{cap_id}: {list_field} must be a list")
        if not isinstance(capability.get("emmaCritical"), bool):
            errors.append(f"{cap_id}: emmaCritical must be boolean")

    return {
        "schema": "temple-ai-studio.capability-registry-validation.v1",
        "registry": str(path),
        "overall": "PASS" if not errors else "FAIL",
        "capabilityCount": len(capabilities),
        "dimensionCount": len(dimensions),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Temple AI Studio capability registry.")
    parser.add_argument("--registry", default="evaluations/capability-registry.json")
    parser.add_argument("--output", help="Optional path for validation JSON.")
    args = parser.parse_args()

    report = validate(Path(args.registry))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
