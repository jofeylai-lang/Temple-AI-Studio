# AI Reasoning Pipeline V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Purpose

This document defines how Temple AI Studio thinks when transforming a user's Chinese request into a finished Temple product video.

It describes the internal reasoning workflow, decision sequence, validation logic, recovery behavior, and definition of done.

This document does not define code, UI, APIs, or implementation details.

This document does not contain reusable production prompts.

## Core Principle

Temple AI Studio should not immediately generate media from a user's request.

It should first understand the user's intent, load the correct product and brand knowledge, plan the story, plan each scene, generate structured creative instructions, validate the result, and only then prepare the export package.

The system should think like a product marketer, creative director, brand guardian, and production coordinator.

## Pipeline Overview

The reasoning pipeline has ten stages:

1. User Intent Analysis
2. Knowledge Loading
3. Story Planning
4. Scene Planning
5. Prompt Generation
6. Model Selection Logic
7. Quality Check
8. Export Package
9. Failure Recovery
10. Definition of Done

Each stage produces structured decisions that guide the next stage.

## 1. User Intent Analysis

The first task is to understand what the user is asking for in Chinese.

The system should interpret natural Chinese, including short, incomplete, informal, or emotionally described requests.

The system should not assume the user knows marketing structure, video structure, prompt structure, or platform requirements.

### Understand the Chinese Request

The system should identify:

- What product the user wants to promote
- What feeling the user wants the video to create
- What the user wants the viewer to understand
- What platform or usage context is implied
- Whether the user is asking for a draft, final export, revision, or regeneration

If the request is vague, the system should infer a reasonable default while preserving uncertainty in the project notes.

### Detect Product Type

The system should classify the product type.

Possible product types include:

- Candle
- Spiritual object
- Course
- Service
- Event
- Digital product
- Physical product
- Membership
- Consultation
- Ritual tool
- Lifestyle product

The product type affects:

- Visual direction
- Feature emphasis
- Story rhythm
- CTA style
- Risk level for claims
- Platform caption style

### Detect Target Audience

The system should identify the likely audience.

Possible audience types include:

- Existing Temple followers
- New social media viewers
- Spiritual lifestyle customers
- Meditation users
- Gift buyers
- Event participants
- Returning members
- General consumers

Audience affects:

- How much context is needed
- Whether the tone should be educational or emotional
- Whether the product should be explained directly or introduced softly
- How strong the CTA should be

### Detect Marketing Objective

The system should identify the primary marketing objective.

Possible objectives include:

- Awareness
- Product introduction
- Soft selling
- Direct conversion
- Event signup
- Brand trust
- Education
- Ritual inspiration
- Re-engagement

The objective determines:

- Scene order
- CTA strength
- Product visibility
- Caption structure
- Thumbnail emphasis

### Intent Analysis Output

At the end of this stage, the system should know:

- Product identity
- Product type
- Target audience
- Marketing objective
- Desired tone
- Target platform
- Required output format
- Missing or uncertain information

## 2. Knowledge Loading

After intent analysis, the system loads the relevant knowledge needed to reason correctly.

Knowledge loading should happen before story or scene generation.

### Temple Brand DNA

The system should load Temple's brand rules.

Required brand knowledge:

- Tone of voice
- Writing style
- Subtitle style
- Logo usage principles
- Color identity
- CTA style
- Claims to avoid
- Emotional boundaries

The brand DNA prevents the output from becoming too loud, too commercial, too mystical, or inconsistent with Temple's identity.

### Product Information

The system should load all available product information.

Relevant product knowledge:

- Product name
- Product category
- Product description
- Product photos
- Key features
- Main selling point
- Usage scenario
- Brand notes
- Existing product copy
- Previous approved outputs

If product information is incomplete, the system should proceed with a conservative draft and mark missing information for review.

### Content Model

The system should load the standard Temple product video content model.

Required content structure:

- Hook
- Introduction
- Product Features
- Spiritual Value
- Call To Action
- Ending

The content model ensures every video has a consistent structure while still allowing creative variation.

### Product Spec

The system should load the first product specification.

Required product rules:

- Input expectations
- Output expectations
- Must-have content
- Out-of-scope boundaries
- Acceptance criteria

The product spec prevents the reasoning process from expanding into unsupported capabilities.

### Knowledge Loading Output

At the end of this stage, the system should have:

- Brand constraints
- Product facts
- Standard video structure
- Product rules
- Known limitations
- Missing inputs

## 3. Story Planning

Story planning converts the user's request and loaded knowledge into a complete video outline.

The system should plan before generating any scene-level details.

### Build the Complete Video Outline

The system should decide:

- Main message
- Emotional promise
- Product role
- Viewer transformation
- CTA direction
- Scene count
- Estimated duration

The outline should be understandable without seeing the final video.

### Decide Scene Order

Scene order should follow Temple's default product video arc unless there is a clear reason to adjust it.

Default order:

1. Hook
2. Introduction
3. Product Features
4. Spiritual Value
5. Call To Action
6. Ending

For shorter videos, some sections can be combined.

For example:

- Introduction and Product Features can be one scene.
- Call To Action and Ending can be one scene.

For longer videos, features and spiritual value can be expanded into multiple scenes.

### Determine Emotional Rhythm

The system should decide how the viewer should feel at each point.

Default emotional rhythm:

1. Recognition: the viewer recognizes a need or feeling.
2. Calm attention: the product is introduced without pressure.
3. Trust: the product's concrete value becomes clear.
4. Meaning: the product connects to ritual, emotion, or intention.
5. Invitation: the viewer receives a clear next step.
6. Closure: the brand leaves a calm final impression.

The emotional rhythm should avoid sudden pressure, exaggerated claims, or chaotic pacing.

### Story Planning Output

At the end of this stage, the system should have:

- Video concept
- Scene count
- Scene order
- Emotional rhythm
- Duration target
- CTA direction
- Product emphasis level

## 4. Scene Planning

Scene planning converts the story outline into individual scene decisions.

Every scene should have a clear job.

No scene should exist only because the video needs more length.

### Scene Decision Fields

For every scene, the system should decide:

- Purpose
- Duration
- Visual goal
- Narration goal
- Subtitle goal

### Purpose

The purpose explains why the scene exists.

Examples of purpose categories:

- Capture attention
- Introduce product
- Show product detail
- Explain use case
- Create emotional value
- Build trust
- Invite action
- Close with brand memory

### Duration

Duration should match the scene's purpose and platform.

Short scenes are used for:

- Hook
- Transition
- Final brand memory

Longer scenes are used for:

- Product explanation
- Feature clarity
- Emotional or ritual context

### Visual Goal

The visual goal defines what the viewer should see and understand.

It should specify:

- Whether the product must be clearly visible
- Whether the focus is detail, lifestyle, mood, or brand
- Whether the visual should be static, slow-moving, or expressive
- Whether source product photos must be preserved closely

### Narration Goal

The narration goal defines what the voiceover should communicate.

It should specify:

- Main message of the scene
- Emotional tone
- Level of detail
- Whether product name should be spoken
- Whether the line should be poetic, practical, or direct

### Subtitle Goal

The subtitle goal defines how the text should support the scene.

It should specify:

- Whether the subtitle should summarize or mirror narration
- How short it should be
- Whether product name appears
- Whether CTA wording appears
- Whether emotional language or feature language is preferred

### Scene Planning Output

At the end of this stage, every scene should have:

- A clear role in the video
- Estimated duration
- Visual direction
- Narration direction
- Subtitle direction
- Relationship to the overall story

## 5. Prompt Generation

Prompt generation converts scene decisions into creative instructions for different output types.

This stage should produce structured prompt-ready guidance, but not bypass review.

This document does not include actual prompts.

### Image Prompt Reasoning

For image generation, the system should decide:

- Product visibility level
- Composition
- Lighting
- Background
- Mood
- Color direction
- Brand consistency
- Source image fidelity
- Platform-safe framing

The image prompt should protect the product identity and avoid visual changes that misrepresent the product.

### Video Prompt Reasoning

For video generation, the system should decide:

- Camera movement
- Product movement
- Scene motion
- Duration
- Pacing
- Realism level
- Transition intent
- What must remain stable

The video prompt should avoid unnecessary motion. Temple videos should feel intentional and calm.

### Narration Prompt Reasoning

For narration, the system should decide:

- Voice tone
- Speaking pace
- Emotional temperature
- Sentence length
- Brand vocabulary
- Whether the line is explanatory or poetic

Narration should sound natural in Traditional Chinese.

### Subtitle Prompt Reasoning

For subtitles, the system should decide:

- Condensed wording
- Reading speed
- Line breaks
- Emphasis
- Whether to simplify narration
- Whether to include product name

Subtitles should be readable even on mobile.

### Thumbnail Prompt Reasoning

For thumbnail generation or selection, the system should decide:

- Best product frame
- Main visual focus
- Short cover text direction
- Brand presence
- Emotional hook
- Platform suitability

The thumbnail should make the product and mood understandable at a glance.

### Prompt Generation Output

At the end of this stage, the system should have generation-ready guidance for:

- Image
- Video
- Narration
- Subtitle
- Thumbnail

Each output should remain connected to the same story plan and brand DNA.

## 6. Model Selection Logic

Temple AI Studio should choose between local models and cloud models based on the job, quality requirement, cost, privacy, and reliability.

The system should not choose a model only because it is available.

### Use Local Models When

Local models are preferred when:

- Privacy is important
- The product materials should stay local
- The task is simple
- Draft speed is acceptable
- Cost should be minimized
- The output is for internal review
- The required quality is achievable locally

Examples of local-friendly tasks:

- Draft image generation
- Prompt testing
- Simple product visuals
- Local portrait motion tests
- Subtitle/caption preparation
- Metadata preparation

### Use Cloud Models When

Cloud models are preferred when:

- Human motion realism is important
- Complex motion or higher-quality media is needed
- Product video quality must be higher than local tools can produce
- Better camera motion is required
- Commercial-level output is needed
- User has approved account, credits, or API access

Cloud use should require awareness of:

- Cost
- Login requirements
- Usage rights
- Privacy
- Platform restrictions
- Manual approval

### Hybrid Workflow

A hybrid workflow is acceptable when:

- Temple AI Studio prepares story, prompts, metadata, subtitles, and review structure locally
- A cloud model generates the difficult media
- Final review and export package remain organized in Temple AI Studio

This is likely the most practical path for high-quality product video V1.

### Model Selection Output

At the end of this stage, the system should know:

- Which generation path is recommended
- Why it was chosen
- What limitations apply
- Whether user approval is needed
- Whether an alternative path exists

## 7. Quality Check

Before export, the system should validate the generated content and media.

Quality check should happen before the user treats the result as final.

### Content Validation

The system should verify:

- Product name is correct
- Product type is consistent
- Main selling point is present
- Scene order makes sense
- Hook is clear
- CTA is clear
- Caption is usable
- SEO keywords exist
- Thumbnail suggestion exists

### Brand Validation

The system should verify:

- Tone matches Temple Brand DNA
- Writing is calm and premium
- CTA is not aggressive
- Claims are not exaggerated
- Spiritual value is grounded
- Subtitles are concise
- Logo usage is restrained
- Color direction is brand-aligned

### Scene Validation

The system should verify each scene has:

- Purpose
- Duration
- Visual goal
- Narration goal
- Subtitle goal
- Prompt guidance
- Music direction
- Transition direction

### Media Validation

When preview media exists, the system should verify:

- Product is visible when needed
- Video ratio matches target platform
- Duration is within target range
- Subtitles are readable
- Audio exists if narration is expected
- Output is not obviously corrupted
- Export file exists

### Review Status

The result should be marked as one of:

- Draft
- Needs revision
- Approved
- Exported
- Failed

Only approved content should become final export.

## 8. Export Package

The final deliverable should include everything needed for manual review, reuse, and posting.

### Required Export Package

Every completed Temple product video should include:

- Final video file
- Caption text
- Subtitle text
- Scene list
- Thumbnail suggestion
- Metadata record
- Source material references
- Review status

### Recommended Export Package

When available, also include:

- Draft preview
- Previous scene versions
- Regeneration notes
- Platform-specific caption variants
- SEO keyword list
- Music direction notes
- Thumbnail frame reference

### Export Package Purpose

The export package should make it clear:

- What was generated
- Why it was generated
- Which product it belongs to
- Which platform it targets
- Which inputs were used
- Whether it is approved
- Where the final file is located

## 9. Failure Recovery

Failure recovery should preserve user work and avoid forcing the user to restart.

The system should identify which stage failed and recover from the nearest completed stage.

### Intent Analysis Failure

If the user request is too unclear, the system should ask for missing information in plain Chinese.

It should preserve any useful partial understanding.

### Knowledge Loading Failure

If product or brand information is missing, the system should continue with conservative defaults and mark the missing information for review.

If required product data is missing, such as product name or product image, the system should request it before generation.

### Story Planning Failure

If a complete video outline cannot be created, the system should create a simpler structure and flag it for review.

The user should be able to revise the product description or objective.

### Scene Planning Failure

If one scene cannot be planned, the system should keep the rest of the video plan and regenerate only the failed scene plan.

### Prompt Generation Failure

If prompt guidance fails for one output type, the system should preserve the scene plan and retry only that prompt category.

For example:

- Retry image guidance only
- Retry video guidance only
- Retry narration guidance only
- Retry subtitle guidance only
- Retry thumbnail guidance only

### Model Generation Failure

If local generation fails, the system should preserve the prompt, source materials, metadata, and scene plan.

The user can:

- Retry local generation
- Switch to a cloud path if approved
- Save as draft
- Regenerate only the failed scene

If cloud generation fails, the system should preserve all local preparation and provide a clear manual retry path.

### Quality Check Failure

If quality validation fails, the system should identify the exact weak part.

The user should be able to:

- Regenerate a single scene
- Edit text
- Replace product material
- Change target platform
- Reject the draft

### Export Failure

If export fails, the system should preserve the approved preview and all content records.

The user should be able to retry export without regenerating the video.

### Recovery Output

After any failure, the system should show:

- What failed
- What was preserved
- What can be retried
- What user action is needed
- The safest next step

## 10. Definition of Done

The reasoning pipeline is complete when it can transform one Chinese product video request into a complete Temple product video package.

Required final conditions:

1. User intent is understood.
2. Product type is identified.
3. Target audience is identified.
4. Marketing objective is identified.
5. Temple Brand DNA is applied.
6. Product information is loaded.
7. Content Model is followed.
8. Product Spec boundaries are respected.
9. Complete video outline is created.
10. Scene order is defined.
11. Emotional rhythm is defined.
12. Every scene has purpose, duration, visual goal, narration goal, and subtitle goal.
13. Generation guidance exists for image, video, narration, subtitle, and thumbnail.
14. Local vs cloud model path is selected with a clear reason.
15. Quality checks pass or unresolved issues are clearly marked.
16. Export package includes final video, caption, subtitles, scene list, thumbnail suggestion, metadata, source references, and review status.
17. Failure recovery can resume from the nearest completed stage.
18. Final output is understandable, reviewable, and ready for manual posting.

The pipeline should be considered successful only when it produces a traceable, brand-aligned, reviewable Temple product video package, not just a media file.

## Stop Point

This document defines the AI reasoning pipeline only.

No implementation should begin until this reasoning pipeline is reviewed and approved.
