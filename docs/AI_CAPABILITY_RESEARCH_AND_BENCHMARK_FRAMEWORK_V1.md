# AI Capability Research And Benchmark Framework V1

Status: Active Framework

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`
- `BENCHMARK_PROTOCOL_V1.md`
- `PROVIDER_EVALUATION_MATRIX_V1.md`

## Mission

Build a unified benchmarking framework for every major capability inside Temple AI Studio.

Temple AI Studio should optimise the entire capability stack, not individual software.

## Capabilities Covered

- LLM
- Image Generation
- Identity Preservation
- Character Training
- Video Generation
- Talking Head
- Full Body Animation
- Lip Sync
- Voice Cloning
- TTS
- Subtitle
- Editing
- Music
- Automation

## Framework Assets

Capability registry:

```text
evaluations/capability-registry.json
```

Generated benchmark work packages:

```text
evaluations/capabilities/<capability-id>/BENCHMARK_WORK_PACKAGE.md
```

Generator:

```text
scripts/temple_ai_studio/generate_capability_benchmarks.py
```

Index:

```text
evaluations/capabilities/capability-benchmark-index.json
```

Research matrix:

```text
research/current/2026-07-24-ai-capability-research-matrix.md
```

## Required Method For Every Capability

For each capability:

1. Research current state of the art.
2. Benchmark current implementation.
3. Benchmark better local approaches.
4. Benchmark reputable free services.
5. Benchmark reputable paid services.
6. Produce measurable comparison.
7. Recommend:
   - Keep current
   - Improve current
   - Replace current
8. If replacement is recommended, prove the current solution has already reached its practical limit.

## Evaluation Dimensions

Every capability is evaluated on:

- quality
- stability
- maintainability
- cost
- privacy
- local capability
- automation potential
- Emma consistency

## Scoring

Each dimension receives a 0-5 score.

| Score | Meaning |
| ---: | --- |
| 0 | Not measured or unusable |
| 1 | Severe limitation |
| 2 | Works only with heavy manual repair |
| 3 | Usable for controlled cases |
| 4 | Strong production candidate |
| 5 | Production-grade for Temple needs |

## Replacement Gate

Replacement is not allowed unless:

1. Current implementation has a measured baseline.
2. Current implementation has been optimised.
3. Latest relevant workflows, nodes, plugins, models and community techniques have been tested.
4. Practical limits are documented.
5. Replacement candidate has measurable advantage.
6. Migration cost is documented.
7. Maintenance cost is documented.
8. Privacy and cost impact are documented.
9. CEO approves if paid service activation is required.

## Current Stack Baseline

| Capability | Current Status | Current Implementation |
| --- | --- | --- |
| LLM | Partial | Codex/OpenAI-assisted engineering and local rule-based generation |
| Image Generation | Missing production provider | Uploaded photos and placeholder frame generation |
| Identity Preservation | Governance only | Emma rules defined, no scorer |
| Character Training | Blocked by source material | Not started |
| Video Generation | Basic local baseline | FFmpeg image assembly |
| Talking Head | Candidate needed | Not production-connected |
| Full Body Animation | Research needed | Not production-ready |
| Lip Sync | Candidate needed | Not production-connected |
| Voice Cloning | Candidate needed | Not production-connected |
| TTS | Missing audio provider | Text narration files only |
| Subtitle | Basic local baseline | Timeline-based SRT |
| Editing | Working baseline | FFmpeg local rendering |
| Music | Research needed | Not connected |
| Automation | Partial | V1 app workflow, backup, restore, support package, quality checker |

## Practical Use

When a new tool is proposed:

1. Add or update it in `capability-registry.json`.
2. Regenerate benchmark work packages.
3. Complete the capability benchmark.
4. Store evidence in `evaluations/`.
5. Update research in `research/current/`.
6. Recommend keep, improve or replace.

## Definition Of Done

Framework V1 is complete when:

- all major capabilities are registered
- benchmark work packages exist for each capability
- scoring dimensions are standardized
- replacement gate is documented
- current-state research matrix exists
- generation script validates the registry and produces benchmark packages
- the framework is committed for future iterations
