# Subtitle Capability Benchmark Work Package

Capability ID:

```text
subtitle
```

Status:

Draft benchmark work package

Generated:

```text
2026-07-24T10:34:09
```

## Purpose

Generate, align, style and validate Traditional Chinese subtitles.

## Current Implementation

```text
V1 generates timeline-based SRT from scene durations.
```

Current status:

```text
basic-local-baseline
```

## Benchmark Target

Measure timing accuracy, readability, line length, safe area, and Traditional Chinese quality.

## Candidates

### Current Solution

Benchmark the current Temple AI Studio implementation first.

### Better Local Approaches

- Whisper
- WhisperX
- faster-whisper
- rule-based timeline generation

### Reputable Free Services

- free transcription tiers where privacy-safe

### Reputable Paid Services

- OpenAI transcription
- Google Speech-to-Text
- commercial subtitle APIs

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
| quality | 0 | Not measured | | |
| stability | 0 | Not measured | | |
| maintainability | 0 | Not measured | | |
| cost | 0 | Not measured | | |
| privacy | 0 | Not measured | | |
| localCapability | 0 | Not measured | | |
| automationPotential | 0 | Not measured | | |
| emmaConsistency | 0 | Not measured | | |

## Emma Consistency

Emma critical:

```text
false
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
