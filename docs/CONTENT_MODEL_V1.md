# Content Model V1

Product: Temple Product Video Generator

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This document follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `AI_REASONING_PIPELINE_V1.md`

## Purpose

This document defines the standard content model for every generated Temple product video.

It is the single source of truth for video structure, scene content, brand voice, metadata, and regeneration rules.

This document does not define code, UI, APIs, or implementation details.

## 1. Overall Video Structure

Every Temple product video follows this core arc:

1. Hook
2. Introduction
3. Product Features
4. Spiritual Value
5. Call To Action
6. Ending

Recommended V1 length:

- Short version: 15 seconds
- Standard version: 30 seconds
- Extended version: 45 seconds

Default V1 format:

- Vertical 9:16
- Traditional Chinese
- Suitable for Instagram Reels, TikTok, YouTube Shorts, and Shorts

### Hook

Purpose:

Capture attention with a relatable feeling, situation, or desire.

Example direction:

```text
忙了一整天，你需要一個讓自己安定下來的時刻。
```

### Introduction

Purpose:

Introduce the product naturally and connect it to the viewer's situation.

Example direction:

```text
Temple Energy Candle，是為夜晚靜心準備的日常儀式蠟燭。
```

### Product Features

Purpose:

Explain concrete product qualities in simple language.

Feature types may include:

- Material
- Scent
- Handmade process
- Design
- Size
- Usage scenario
- Packaging
- Duration

Example direction:

```text
溫和香氣、乾淨燃燒、簡約外觀，讓空間更容易進入安靜狀態。
```

### Spiritual Value

Purpose:

Explain the deeper emotional, ritual, or spiritual value without making exaggerated claims.

Example direction:

```text
點亮它，不是為了逃離生活，而是為了重新聽見自己。
```

### Call To Action

Purpose:

Invite the viewer to take one simple next step.

Example direction:

```text
為你的靜心時刻，準備一盞溫柔的光。
```

### Ending

Purpose:

Close with product name, brand name, logo, final product shot, or a short closing line.

Example direction:

```text
Temple
讓儀式回到生活。
```

## 2. Scene Model

Default V1 scene count:

- 15 seconds: 3 scenes
- 30 seconds: 4 to 5 scenes
- 45 seconds: 5 to 7 scenes

Each scene must define:

- Purpose
- Estimated Duration
- Visual Description
- Narration
- Subtitle
- Prompt direction
- Music
- Transition
- Optional Effects

### Scene 1: Hook

Purpose:

Create immediate emotional relevance.

Estimated Duration:

2 to 4 seconds.

Visual Description:

A quiet opening visual that reflects the viewer's need, mood, or daily situation.

Narration:

One short Traditional Chinese sentence that speaks to the viewer's inner state.

Subtitle:

Short, readable, and emotionally clear.

Prompt Direction:

Describe mood, lighting, composition, product presence, and emotional setting.

Music:

Soft ambient, ritual, meditation, piano, warm pad, or subtle cinematic texture.

Transition:

Slow fade, soft dissolve, or gentle push-in.

Optional Effects:

Light glow, candle flicker, soft shadow movement, slow camera drift.

### Scene 2: Product Introduction

Purpose:

Show the product clearly and name it.

Estimated Duration:

3 to 6 seconds.

Visual Description:

The main product image or product shot should be clear and recognizable.

Narration:

Introduce product name and primary use.

Subtitle:

Product name plus a concise phrase.

Prompt Direction:

Emphasize product clarity, premium presentation, natural lighting, and clean composition.

Music:

Continue the same music bed.

Transition:

Clean cut, soft dissolve, or slow reveal.

Optional Effects:

Subtle highlight, gentle product focus, shallow depth impression.

### Scene 3: Product Features

Purpose:

Explain what the product is and why it is useful.

Estimated Duration:

4 to 8 seconds.

Visual Description:

Close-up or detail-focused visuals showing texture, packaging, use context, or material qualities.

Narration:

Mention 1 to 3 concrete product features.

Subtitle:

Short feature phrases.

Prompt Direction:

Keep visual direction grounded in uploaded product materials.

Music:

Steady and calm.

Transition:

Cut on detail, gentle pan, or dissolve between detail shots.

Optional Effects:

Text emphasis, soft highlight, slow zoom, gentle particles only if brand-appropriate.

### Scene 4: Spiritual Value

Purpose:

Connect the product to Temple's deeper emotional and ritual value.

Estimated Duration:

4 to 8 seconds.

Visual Description:

Show the product in a meaningful environment: meditation corner, quiet room, altar, evening table, reading space, ritual setup, or calm lifestyle context.

Narration:

One sentence connecting the product to intention, grounding, ritual, calm, reflection, or inner clarity.

Subtitle:

Poetic but clear.

Prompt Direction:

Describe atmosphere and ritual context. Avoid supernatural claims.

Music:

Warm, spacious, and emotionally steady.

Transition:

Slow fade, light bloom, or natural motion continuation.

Optional Effects:

Warm light movement, breath-like pacing, soft focus background.

### Scene 5: Call To Action

Purpose:

Tell the viewer what to do next.

Estimated Duration:

3 to 5 seconds.

Visual Description:

Product hero shot, product in use, packaging shot, or final lifestyle shot.

Narration:

One simple invitation.

Subtitle:

Clear CTA, preferably one line.

Prompt Direction:

Keep product and brand visible.

Music:

Slightly resolves or settles.

Transition:

Fade to final card or soft end frame.

Optional Effects:

Logo reveal, gentle light fade, final text lockup.

### Scene 6: Ending

Purpose:

Leave a final brand memory.

Estimated Duration:

2 to 4 seconds.

Visual Description:

Brand name, product name, logo, or final still frame.

Narration:

Optional. The ending can be silent if the visual is strong.

Subtitle:

Brand line, product name, or closing phrase.

Prompt Direction:

Simple, clean, centered, premium, calm.

Music:

Resolve naturally.

Transition:

Fade out.

Optional Effects:

Logo fade, subtle glow, final hold.

## 3. Metadata Model

Every Temple product video must include metadata.

Required metadata:

- Product Name
- Tags
- Caption
- SEO Keywords
- Thumbnail Suggestion
- Product category
- Target platform
- Video length
- Tone
- Main selling point
- Source image reference
- Scene count
- Review status
- Export status
- Created date
- Version

### Product Name

The exact product name used in the video.

### Tags

Tags should describe product type, mood, audience, platform, and campaign.

Example:

```text
candle, meditation, ritual, calm, temple, reels, product-video
```

### Caption

Caption should be ready for manual posting.

Caption style:

- Traditional Chinese
- Calm and clear
- 1 to 3 short paragraphs
- Optional hashtags
- No excessive emoji
- No exaggerated claims

Example:

```text
忙了一整天，留一點時間給自己。

Temple Energy Candle，為夜晚的靜心與儀式感而準備。

#Temple #靜心 #儀式感 #蠟燭 #日常療癒
```

### SEO Keywords

SEO keywords support future search, content planning, website copy, and captions.

Example:

```text
靜心蠟燭, 冥想蠟燭, 儀式感生活, 香氛蠟燭, Temple Energy Candle
```

### Thumbnail Suggestion

The thumbnail suggestion describes the best frame or image for the video cover.

Example:

```text
使用蠟燭點亮後的近距離產品畫面，背景保持溫暖、乾淨，文字放「給夜晚的一盞安定」。
```

## 4. Temple Brand DNA

Temple product videos must feel intentional, calm, premium, spiritual, and grounded.

Temple should not feel loud, cheap, manipulative, exaggerated, or overly mystical.

### Tone of Voice

Temple's tone should be:

- Calm
- Clear
- Warm
- Reflective
- Premium
- Trustworthy
- Ritual-oriented

Temple's tone should not be:

- Pushy
- Fear-based
- Overly sales-driven
- Superstitious
- Overpromising
- Loud
- Cheap

### Writing Style

Writing should be:

- Traditional Chinese by default
- Short sentences
- Natural spoken rhythm
- Emotionally grounded
- Clear enough for social video
- Slightly poetic but not abstract

Good writing pattern:

```text
先說出一個感受。
再帶出產品。
最後給一個溫柔但清楚的行動。
```

### Subtitle Style

Subtitle should be:

- Traditional Chinese
- One to two lines per scene
- Easy to read quickly
- Shorter than narration when needed
- Calm and clean

### Logo Usage

Logo should be used sparingly.

Recommended usage:

- Final scene
- Thumbnail
- Product ending card

Logo should feel like a signature, not an interruption.

### Color Identity

Recommended color direction:

- Warm white
- Soft gold
- Deep charcoal
- Natural green
- Candlelight amber
- Muted earth tones

Avoid:

- Neon colors
- Harsh red
- Oversaturated purple
- Cheap gold effects
- Busy gradient backgrounds
- Colors that make subtitles hard to read

### CTA Style

Temple's CTA should be direct but gentle.

Good CTA patterns:

```text
為你的夜晚，留一盞安定的光。
```

```text
把儀式感，帶回你的日常。
```

Avoid CTA patterns:

```text
立刻購買！
錯過就沒有！
保證改變人生！
```

## 5. Regeneration Rules

The product should allow regeneration at a specific content level.

Can be regenerated independently:

- Hook line
- Hook visual direction
- One scene
- Scene narration
- Scene subtitle
- Scene prompt direction
- Scene music direction
- Scene transition suggestion
- Caption
- Hashtags
- SEO keywords
- Thumbnail suggestion
- CTA wording
- Ending line

Should not change without user approval:

- Product name
- Main product image
- Main selling point
- Target platform
- Approved scenes
- Approved caption

Full video regeneration should only happen when:

- User explicitly chooses regenerate full video
- Product direction changes
- Target platform changes
- Product image changes significantly
- User rejects the entire draft

Regeneration history should preserve:

- What changed
- Which scene changed
- Which version is current
- Whether previous version can be restored

## 6. Definition of Done

A Temple product video content package is done when all required content parts are complete and reviewable:

1. Product name
2. Product description
3. Main selling point
4. Target platform
5. Video structure
6. Scene list
7. Hook
8. Introduction
9. Product features
10. Spiritual value
11. Call to action
12. Ending
13. Narration for every scene
14. Subtitle for every scene
15. Prompt direction for every scene
16. Music direction
17. Transition direction
18. Caption
19. SEO keywords
20. Thumbnail suggestion
21. Tags
22. Review status

Quality requirements:

- Product is clearly identifiable.
- Video has a clear emotional arc.
- Content follows Temple Brand DNA.
- Video does not overpromise spiritual results.
- CTA is clear but not aggressive.
- Subtitles are readable and concise.
- Caption is suitable for manual posting.
- Metadata is complete enough for future search and reuse.
- Regenerated scene does not break the rest of the video.
