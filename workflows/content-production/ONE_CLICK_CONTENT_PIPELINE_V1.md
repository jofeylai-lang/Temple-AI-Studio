# One-Click Content Pipeline V1

Status: Target Workflow

Date: 2026-07-24

Authority:

- `docs/TEMPLE_AI_CONSTITUTION.md`
- `docs/MASTER_PROJECT_OS_FOUNDATION_V1.md`

## Purpose

Define the long-term operating workflow for Temple AI Studio.

## CEO Input

The ideal input is one Traditional Chinese sentence.

Examples:

```text
幫我做一支介紹這款能量蠟燭的 IG Reels。
```

```text
讓 Emma 介紹今天的新品，風格溫柔、有儀式感。
```

## Pipeline

```text
Traditional Chinese request
-> intent analysis
-> missing material check
-> research if needed
-> script
-> storyboard
-> asset plan
-> provider selection
-> image/video generation
-> voice generation
-> subtitle generation
-> edit assembly
-> quality gates
-> targeted regeneration
-> export package
-> CEO approval
```

## Stage Contracts

### 1. Intent Analysis

Input:

- CEO sentence
- optional source material

Output:

- content type
- product/Emma requirement
- target platform
- tone
- business objective
- missing material list

### 2. Research

Run when:

- technology choice is unclear
- current trends matter
- provider replacement is being considered
- new workflow is needed

Output:

- research brief
- source links
- benchmark candidates

### 3. Script

Output:

- hook
- narration
- CTA
- platform caption draft

### 4. Storyboard

Output:

- scene list
- duration
- visual direction
- subtitle
- provider requirements

### 5. Asset Generation

Output:

- images
- clips
- voice
- subtitles
- prompts
- metadata

### 6. Edit Assembly

Output:

- preview video
- final video candidate
- export package

### 7. Quality Gates

Output:

- PASS/FAIL report
- failed components
- targeted regeneration plan

### 8. CEO Approval

CEO receives:

- finished video candidate
- simple PASS/FAIL summary
- export location

CEO should not receive:

- raw technical logs unless requested
- provider debugging burden
- step-by-step engineering tasks

## Failure Recovery

If a stage fails:

1. Preserve approved upstream outputs.
2. Identify failed component.
3. Regenerate only failed component.
4. Re-run quality gate.
5. Escalate only if CEO decision is required.

## Definition Of Done

One-Click Content Pipeline V1 is complete when it can be implemented as a reusable orchestration layer above individual Temple products.
