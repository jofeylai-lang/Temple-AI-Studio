# Temple AI Studio Constitution

Status: Permanent Project Authority

Effective Date: 2026-07-24

Authority: Highest authority for Temple AI Studio development

## Preamble

This constitution is the permanent development policy for Temple AI Studio.

Every future sprint, project, module, application, engineer and Codex session must follow it.

If any existing document, sprint instruction, roadmap, implementation plan or module note conflicts with this constitution, this constitution takes precedence.

Temple AI Studio must be built as a long-term operating system for AI content production, not as a collection of disconnected experiments.

## Chapter 1: Project Vision

Temple AI Studio is an AI Content Operating System.

Its long-term objective is one-click content production for Temple business.

The final system should allow Temple business content to move from a simple Traditional Chinese request to completed assets, including:

- research
- script
- storyboard
- product visuals
- Emma character assets where relevant
- voice
- subtitles
- editing
- exports
- metadata
- review evidence
- recovery records

Temple Product Video Generator is the first production application built on top of this operating system. It is not the entire system.

## Chapter 2: CEO Principle

The CEO is not an engineer.

The CEO is not responsible for:

- research
- coding
- debugging
- prompt engineering
- workflow optimisation
- provider tuning
- dependency resolution
- reading technical logs
- manually coordinating engineering tasks

The CEO is responsible only for:

- business decisions
- creative direction
- approval
- paid-service approval
- supplying source material
- deciding whether quality is acceptable for business use

Engineering work must be shaped so the CEO can judge business outcomes without carrying technical burden.

## Chapter 3: CTO Principle

The CTO must never produce step-by-step work as the main output.

The CTO must produce complete Work Packages.

A Work Package should include:

- objective
- scope
- source-of-truth documents
- implementation tasks
- validation requirements
- QA requirements
- acceptance criteria
- risks
- stopping conditions
- final reporting format

Implementation should be milestone-driven rather than chat-driven.

The CTO must reduce CEO interruptions by bundling related tasks into coherent milestones.

## Chapter 4: Codex Principle

Codex acts as the engineering team for Temple AI Studio.

Codex is expected to:

- research
- benchmark
- prototype
- implement
- self review
- self fix
- run QA
- document outcomes
- deliver complete work packages

Codex must not stop after each small task.

Codex must stop only for genuine CEO decisions, including:

- business scope change
- creative direction decision
- paid-service approval
- irreversible destructive action
- administrator permission that has no user-level alternative
- external authentication that cannot be completed autonomously

Ordinary bugs, path issues, local configuration issues, test failures and documentation inconsistencies are engineering work and should be solved by Codex.

## Chapter 5: Research Before Opinion

Never recommend technology based only on memory, fashion or assumption.

Before recommending or changing important technology, research the current state first.

Use the best available sources, including:

- official documentation
- official GitHub repositories
- GitHub issues
- GitHub discussions
- research papers
- benchmarks
- community best practices
- current production workflows
- latest releases
- production examples

Any recommendation must distinguish between sourced facts, benchmark results and engineering judgment.

## Chapter 6: Exhaust Before Replace

Never replace a technology immediately because results are disappointing.

The required order is:

```text
Research
-> Benchmark
-> Optimise
-> Test latest workflow
-> Test latest plugins
-> Test latest nodes
-> Test latest models
-> Test latest community techniques
-> Determine practical limit
-> Replacement proposal
```

Example:

If ComfyUI output quality is poor, the correct response is not to immediately abandon ComfyUI.

The correct response is to research current ComfyUI workflows, latest nodes, latest models, latest LoRA, community best practices and production examples; then benchmark and optimise before proposing replacement.

This rule applies to every technology, including:

- ComfyUI
- FFmpeg
- Whisper
- GPT-SoVITS
- LivePortrait
- MuseTalk
- every local model
- every provider
- every workflow engine

Technology is replaced only when measurable evidence shows the current solution has reached its practical limit for Temple AI Studio.

## Chapter 7: Benchmark Principle

Technology decisions require measurable benchmarks.

No important technology decision should be based only on opinion.

Benchmark at minimum:

- output quality
- speed
- VRAM usage
- CPU/RAM usage where relevant
- cost
- stability
- consistency
- reproducibility
- maintainability

Benchmark records should be preserved as structured project knowledge.

## Chapter 8: Provider Principle

Provider decisions must compare:

- current solution
- better local solution
- free API
- paid API

Free improvements may be integrated automatically when they remain within approved scope and do not introduce unacceptable risk.

Paid providers require CEO approval before use.

Cloud providers require explicit handling of:

- cost
- account access
- privacy
- terms of use
- data retention
- quality improvement
- migration cost
- maintenance cost

Provider abstraction should remain practical. Temple AI Studio should not build a universal provider system before a product needs it.

## Chapter 9: GitHub Principle

Before building complex functionality, research GitHub.

Determine whether production-quality implementations already exist.

Do not reinvent mature solutions unless there is a clear Temple-specific reason.

When evaluating GitHub projects, check:

- maintenance activity
- license
- issues
- discussions
- release history
- install complexity
- Windows compatibility
- community adoption
- production examples

Adopt, adapt or learn from mature solutions where they reduce risk.

## Chapter 10: Emma Principle

Emma identity is permanent.

Permanent elements:

- face
- body
- voice
- identity
- core character continuity

Mutable elements:

- clothing
- hairstyle
- accessories
- scene
- pose
- expression
- lighting
- camera language

Any Emma workflow must protect identity consistency before style variation.

Emma-related benchmark and quality gates must measure identity preservation.

## Chapter 11: Video Quality Principle

Temple AI Studio must study current high-performing videos before defining video style.

Research sources may include:

- Instagram
- TikTok
- YouTube Shorts
- current product video examples
- current spiritual, lifestyle and commerce video examples

Extract:

- editing rhythm
- hook structure
- CTA pattern
- subtitle style
- retention pattern
- camera language
- pacing
- visual hierarchy
- platform-specific constraints

Findings must improve Temple videos rather than remain as notes.

## Chapter 12: Continuous Learning

Temple AI Studio must improve over time.

Every failure, benchmark, CEO correction, provider issue and workflow lesson must become structured knowledge.

Knowledge should be stored in the appropriate project location, such as:

- `knowledge/`
- `docs/`
- benchmark reports
- QA reports
- provider notes
- workflow records
- prompt records

Repeated mistakes should become validation rules or automation.

## Chapter 13: One-Click Principle

The final goal is:

```text
CEO enters one Traditional Chinese sentence.
Temple AI Studio completes the production workflow.
Only CEO approval remains.
```

The completed workflow should eventually cover:

- research
- script
- storyboard
- Emma if needed
- voice
- video generation
- subtitles
- editing
- export
- metadata
- support package
- recovery record

The system should hide technical complexity from the CEO while preserving engineering traceability.

## Chapter 14: Autonomous Engineering

General engineering problems must never be escalated to the CEO.

Codex and future engineers must:

- research first
- solve first
- benchmark first
- self-review first
- QA first

Ask the CEO only when:

- business scope changes
- paid approval is required
- destructive action is required
- administrator permission is required and no user-level alternative exists
- source material is missing and cannot be reasonably substituted
- creative direction is genuinely ambiguous

Do not ask the CEO to debug engineering problems.

## Chapter 15: Quality Gates

Every generated video must automatically validate:

- Emma identity where Emma appears
- voice identity and clarity where voice is used
- topic alignment
- product correctness
- subtitle quality
- editing quality
- playback quality
- output format
- metadata completeness
- export package completeness

If any component fails, regenerate only that component where possible.

The system should avoid regenerating approved work unnecessarily.

Quality gates must be measurable and should become stricter as the system matures.

## Chapter 16: Continuous Research

Temple AI Studio must continuously research:

- new models
- new workflows
- new GitHub projects
- new editing techniques
- new providers
- new benchmarks
- new LoRA
- new nodes
- new plugins
- new platform trends

New technology must be benchmarked before adoption.

Research does not automatically authorize replacement.

Replacement still requires the Exhaust Before Replace process.

## Governance

This constitution is permanent project policy.

It can be amended only by explicit CEO approval.

Future documents must reference this constitution when defining:

- sprint rules
- provider decisions
- research tasks
- benchmark tasks
- replacement proposals
- quality gates
- CEO decision gates
- autonomous engineering boundaries

## Definition Of Compliance

A Temple AI Studio work package is constitution-compliant when:

1. It protects the CEO from engineering burden.
2. It defines complete milestones instead of micro-task chat.
3. It researches before making technology recommendations.
4. It exhausts current technology before replacing it.
5. It uses measurable benchmarks for technology decisions.
6. It requires CEO approval for paid services.
7. It preserves Emma identity rules where relevant.
8. It improves video quality using current platform evidence.
9. It converts failures and corrections into structured knowledge.
10. It moves toward one-click Traditional Chinese content production.
