# Benchmark Protocol V1

Status: Active Standard

Date: 2026-07-24

Authority:

- `TEMPLE_AI_CONSTITUTION.md`

## Purpose

Define how Temple AI Studio measures technology before adoption, replacement or escalation.

## Required Benchmark Dimensions

Every benchmark must record:

- quality
- speed
- VRAM
- CPU/RAM where relevant
- cost
- stability
- consistency
- reproducibility
- maintainability
- Windows compatibility
- operator complexity

## Benchmark Lifecycle

```text
Research
-> Baseline test
-> Optimised test
-> Repeatability test
-> Failure analysis
-> Recommendation
-> Knowledge capture
```

## Provider Benchmark Requirements

For every provider or workflow, compare:

- current solution
- better local solution
- free API
- paid API

Paid API benchmark can be proposed but not activated without CEO approval.

## Output Format

Every benchmark report must include:

- date
- technology
- version or commit
- source links
- environment
- input material
- workflow used
- settings
- output path
- quality score
- timing
- resource usage
- failures
- reproduction steps
- recommendation

## Initial Benchmark Template

Use:

```text
evaluations/benchmarks/BENCHMARK_TEMPLATE.md
```

## Replacement Rule

Replacement is allowed only after:

1. Current solution baseline has been measured.
2. Current solution has been optimised.
3. Latest releases/workflows/plugins/models have been tested where relevant.
4. Practical limits are documented.
5. Alternative has measurable improvement.
6. Migration and maintenance costs are documented.
7. CEO approves if paid services are involved.

## Definition Of Done

A benchmark is complete when another engineer can reproduce the test and understand why the recommendation was made.
