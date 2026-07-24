from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


DEFAULT_REGISTRY = Path("evaluations/capability-registry.json")
DEFAULT_OUTPUT = Path("evaluations/capabilities")


def slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.lower()).strip("-")


def load_registry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_markdown(capability: dict, registry: dict) -> str:
    dimensions = registry["scoringDimensions"]
    local = "\n".join(f"- {item}" for item in capability.get("localCandidates", [])) or "- None listed"
    free = "\n".join(f"- {item}" for item in capability.get("freeServiceCandidates", [])) or "- None listed"
    paid = "\n".join(f"- {item}" for item in capability.get("paidServiceCandidates", [])) or "- None listed"
    scoring_rows = "\n".join(f"| {dimension} | 0 | Not measured | | |" for dimension in dimensions)
    return f"""# {capability['name']} Capability Benchmark Work Package

Capability ID:

```text
{capability['id']}
```

Status:

Draft benchmark work package

Generated:

```text
{datetime.now().replace(microsecond=0).isoformat()}
```

## Purpose

{capability['purpose']}

## Current Implementation

```text
{capability['currentImplementation']}
```

Current status:

```text
{capability['currentStatus']}
```

## Benchmark Target

{capability['currentBenchmarkTarget']}

## Candidates

### Current Solution

Benchmark the current Temple AI Studio implementation first.

### Better Local Approaches

{local}

### Reputable Free Services

{free}

### Reputable Paid Services

{paid}

Paid services are research candidates only. Activation requires CEO approval.

## Required Research

Research before benchmark:

- official documentation
- official GitHub
- latest releases
- GitHub issues
- GitHub discussions
- current benchmarks
- current production workflows
- community best practices
- Windows installation notes
- licensing and privacy constraints

## Benchmark Dimensions

| Dimension | Score 0-5 | Evidence | Measurement | Notes |
| --- | ---: | --- | --- | --- |
{scoring_rows}

## Emma Consistency

Emma critical:

```text
{str(capability.get('emmaCritical', False)).lower()}
```

If true, benchmark must include identity preservation tests.

## Practical Limit Proof

Replacement cannot be recommended unless all are true:

1. Current solution baseline measured.
2. Current solution optimised.
3. Latest relevant workflows tested.
4. Latest relevant nodes/plugins/models tested.
5. Failure modes documented.
6. Alternative produces measurable improvement.
7. Migration and maintenance cost documented.

## Recommendation

Choose exactly one after benchmark:

- Keep current
- Improve current
- Replace current

Current recommendation:

```text
Not yet measured.
```

## Output Evidence

Record:

- input source path
- output path
- settings
- logs
- quality report
- benchmark report
- screenshots or metadata where relevant

Do not store private CEO source material or generated sensitive media in Git.
"""


def generate(registry_path: Path, output_root: Path) -> list[Path]:
    registry = load_registry(registry_path)
    output_root.mkdir(parents=True, exist_ok=True)
    written = []
    for capability in registry["capabilities"]:
        cap_dir = output_root / slug(capability["id"])
        cap_dir.mkdir(parents=True, exist_ok=True)
        path = cap_dir / "BENCHMARK_WORK_PACKAGE.md"
        path.write_text(render_markdown(capability, registry), encoding="utf-8")
        written.append(path)
    index = {
        "schema": "temple-ai-studio.capability-benchmark-index.v1",
        "generatedAt": datetime.now().replace(microsecond=0).isoformat(),
        "registry": str(registry_path),
        "capabilities": [
            {"id": capability["id"], "name": capability["name"], "workPackage": str((output_root / slug(capability["id"]) / "BENCHMARK_WORK_PACKAGE.md").as_posix())}
            for capability in registry["capabilities"]
        ],
    }
    index_path = output_root / "capability-benchmark-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    written.append(index_path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Temple AI Studio capability benchmark work packages.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    written = generate(Path(args.registry), Path(args.output))
    print(json.dumps({"ok": True, "written": [str(path) for path in written]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
