# Temple AI Studio New Roadmap

Date: 2026-07-23

## Strategic Direction

Temple AI Studio is not the first product.

Temple AI Studio is the operating system.

Products should be built on top of it. The studio should provide shared assets, prompts, workflows, metadata, exports, evaluations, and provider integrations. The products should be small, usable, and easy to validate.

The next phase should avoid building every AI capability first. The project should not add more frameworks, APIs, or providers until one small product proves daily usefulness.

## Product Layer

The project needs a product layer concept before more implementation. This does not require immediate restructuring, but the roadmap should treat future applications as separate products that reuse shared studio capabilities.

Candidate products:

- Temple Product Video Generator
- Temple Reels Generator
- Emma Video Generator
- Social Post Generator

Shared studio capabilities:

- Prompt registry
- Image generation provider
- Video generation provider
- Voice provider
- Subtitle generator
- Metadata recorder
- Platform exporter
- Quality review checklist
- Asset library

## Development Principles

1. Build one small usable application at a time.
2. Reuse current experiments instead of rebuilding.
3. Prefer manual or semi-automated workflows before full automation.
4. Keep local generation and cloud generation as interchangeable options.
5. Require metadata for every generated asset.
6. Require a quality review step before publication.
7. Treat human likeness and voice workflows as governed workflows, not casual experiments.
8. Do not expand provider abstraction until a product needs it.

## Recommended Product Priority

### 1. Temple Product Video Generator

Daily usefulness: High

Business value: High

Ease of completion: Medium

Ease of validation: High

Reason: It can produce clear business assets from product photos, descriptions, and a short script. Success is easy to judge: does it create a useful product video that can be posted or shown to customers?

Recommended scope:

- Input: product name, one product image, target platform, short selling point
- Output: 9:16 video, caption, subtitles, metadata
- First provider path: manual/cloud or ComfyUI-assisted, not a universal engine
- Reuse: `videos/factory`, `prompts/video-factory`, and V1 export folders created only when needed

### 2. Social Post Generator

Daily usefulness: High

Business value: Medium

Ease of completion: High

Ease of validation: High

Reason: It is simpler than video and useful every day. It can validate prompt management, metadata, image exports, and approval workflow without solving difficult motion generation.

Recommended scope:

- Input: topic, audience, platform, image style
- Output: image prompt, post text, hashtags, metadata, one generated/static visual when provider is available
- Reuse: `prompts`, `images`, and V1 output folders created only when needed

### 3. Temple Reels Generator

Daily usefulness: Medium to High

Business value: Medium

Ease of completion: Medium

Ease of validation: Medium

Reason: It can become a repeatable content engine, but needs brand voice, recurring content categories, and quality rules.

Recommended scope:

- Input: topic or lesson
- Output: short script, voiceover text, subtitles, 9:16 export
- Reuse: `brand`, `knowledge`, `voice`, `videos/factory`

### 4. Emma Video Generator

Daily usefulness: Medium

Business value: High if the character becomes a recognizable AI host

Ease of completion: Low to Medium

Ease of validation: Medium

Reason: Human character video is technically harder and has higher governance risk. Existing LivePortrait results are useful, but precise lip-sync and full-body realism are not solved yet.

Recommended scope:

- Input: approved character image, approved voice, script
- Output: talking-head video first
- Later output: controlled full-body video
- Required before implementation: likeness policy, voice policy, quality threshold, allowed platform list

## Feature Ranking Matrix

| Rank | Feature | Daily Usefulness | Business Value | Ease of Completion | Ease of Validation | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Temple Product Video Generator | High | High | Medium | High | Build first |
| 2 | Social Post Generator | High | Medium | High | High | Build second or as support tool |
| 3 | Temple Reels Generator | Medium-High | Medium | Medium | Medium | Build after prompt and export flow stabilize |
| 4 | Image Factory V1 | Medium | Medium | Medium | High | Implement only as needed by products |
| 5 | Video Factory V1 | Medium | High | Low-Medium | Medium | Keep as shared layer, not first product |
| 6 | Emma Video Generator | Medium | High | Low-Medium | Medium | Build after talking-head workflow is reliable |
| 7 | ComfyUI Provider Integration | Medium | Medium | Medium | Medium | Add only for the selected first product workflow |
| 8 | Voice Factory / GPT-SoVITS | Medium | Medium-High | Low | Low-Medium | Defer until voice identity is essential |
| 9 | Telegram Bot | Low-Medium | Medium | Medium | Medium | Defer until there is a product to operate |
| 10 | Website | Low-Medium | Medium | Medium | High | Defer until product positioning is clear |

## 90-Day Roadmap

Constitution note:

`TEMPLE_AI_CONSTITUTION.md` is now the highest project authority. This roadmap is a strategic planning document. Any roadmap sentence that appears to require CEO approval for ordinary engineering work is superseded by the constitution's Autonomous Engineering and CTO principles.

### Phase 0: Stabilize Understanding

Goal: Make the existing project understandable without changing architecture.

Actions:

- Keep this audit report as the baseline.
- Decide whether the public strategic name is Temple AI Studio or Jofey AI Studio.
- Identify which experiments are active, paused, or archive candidates.
- Fix documentation encoding as autonomous engineering work when it blocks readability or delivery.
- Resolve Git safe-directory or local Git configuration issues as autonomous engineering work when they block delivery, unless administrator permission or destructive action is required.

Exit criteria:

- One approved product selected for V1.
- One approved generation path selected.
- One approved output quality bar defined.

### Phase 1: First Small Product

Recommended product: Temple Product Video Generator.

Goal: Build the smallest useful repeatable workflow.

Scope:

- One product input
- One script template
- One visual generation path
- One voice/subtitle path
- One export preset: 9:16
- One metadata record
- One review checklist

Exit criteria:

- Three product videos can be produced with consistent structure.
- Output can be reviewed and accepted or rejected using a checklist.
- The workflow is understandable by reading docs and project folders.

### Phase 2: Shared Factory Extraction

Goal: Extract only the shared pieces proven by the first product.

Scope:

- Prompt registry
- Metadata schema
- Output naming convention
- Provider contract for the one selected provider
- Quality review checklist

Exit criteria:

- Temple Product Video Generator and Social Post Generator can share prompts/metadata/output rules.

### Phase 3: Second Product

Recommended product: Social Post Generator.

Goal: Validate that Temple AI Studio can support more than one small application.

Scope:

- Text post
- Visual prompt
- Platform-specific formatting
- Metadata
- Review checklist

Exit criteria:

- Daily social content can be produced without touching low-level provider details.

### Phase 4: Character Video

Recommended product: Emma Video Generator.

Goal: Create a reliable talking-head character workflow before attempting full-body realism.

Scope:

- Approved character reference
- Approved voice method
- Script input
- Talking-head output
- Subtitle output
- Quality review

Exit criteria:

- Talking-head output is consistent enough for repeated use.
- Likeness and voice consent rules are documented.

## Migration Strategy

Do not start over.

Use the current repository as the foundation, but change the development order.

### Keep Current Structure

Keep the existing folders for now. They already represent the intended operating system:

- `prompts`
- `images`
- `videos`
- `voice`
- `knowledge`
- `workflows`
- `evaluations`
- `outputs`
- `archive`

### Add Product Boundaries Later

Product boundaries should be added through milestone-driven work packages. CEO approval is required only when boundaries change business scope, product identity, paid services, or destructive migration risk.

Potential future direction:

```text
products/
  product-video-generator/
  social-post-generator/
  temple-reels-generator/
  emma-video-generator/
```

This is a future recommendation, not an implemented change.

### Reuse Existing Experiments

Earlier experiment folders were removed from the active repository after the V1 baseline cleanup.

The project should preserve only the lessons learned in documentation:

- Static keyframe assembly was useful as a concept, but not an active V1 asset.
- LivePortrait proved local portrait motion can work, but it is not part of Product Video Generator V1.
- Stable Video Diffusion full-body tests were not suitable for V1 quality.
- Cloud platform handoff notes informed the local/cloud/hybrid decision model, but old handoff assets are not active V1 inputs.

### Separate Experiment From Product

Before coding, define statuses:

- experiment
- candidate
- product-v1
- archived

This can be done in metadata first, without moving files.

### Fix Documentation Before Building More

The corrupted Chinese documentation should be repaired or rewritten before more development. If documentation remains unreadable, the project will lose its accumulated planning value.

### Control Media Growth

Do not commit every generated MP4, GIF, WAV, and image forever. Define which outputs are:

- source references
- working files
- final exports
- archive examples

### Choose One Provider Path

For the first product, select one generation path only.

Recommended options:

1. Cloud platform for high-quality human/product video
2. ComfyUI for local image/video experimentation
3. OpenAI Images or another image provider for static social assets

Avoid implementing five provider integrations before one product works.

## Historical Decision Gates

At the time of this roadmap, the following decisions were open. Later V1 implementation and production deployment resolved several of them. Future work should treat unresolved items through `TEMPLE_AI_CONSTITUTION.md` decision gates:

1. Should the strategic name be Temple AI Studio while the local folder remains Jofey AI Studio?
2. Which product is approved as V1?
3. Should the first product use local ComfyUI, cloud video platforms, or a hybrid workflow?
4. What output quality is acceptable for V1?
5. Should corrupted docs be repaired before product work starts? Resolved: documentation corruption that blocks operations is autonomous engineering work.

## Stop Point

This roadmap was originally analysis only. After adoption of `TEMPLE_AI_CONSTITUTION.md`, future work should not be blocked by this historical stop point. Use constitution stopping conditions instead: business scope change, paid approval, destructive action, administrator permission, missing source material, or genuine creative ambiguity.


