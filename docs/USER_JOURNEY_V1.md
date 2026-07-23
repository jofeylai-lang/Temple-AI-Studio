# User Journey V1

Product: Temple Product Video Generator

Task: Create one Temple product video from start to finish

Date: 2026-07-23

Status: V1 Ready Candidate

## Source of Truth References

This document follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`
- `APP_BLUEPRINT_V1.md`

## Purpose

This document describes the complete user journey for creating one Temple product video.

It is written from the user's perspective. It does not define code, technical architecture, or final UI graphics.

The goal is for a user to understand exactly what happens before the product is built.

## User Goal

The user wants to create one short vertical product video for a Temple product.

The video should be suitable for review before manual posting to Instagram Reels, TikTok, YouTube Shorts, or Shorts.

The user wants to provide simple materials, let AI prepare the video plan, review the result, fix only the weak parts, and export a final version.

## 1. Entry Point

The user enters Temple AI Studio and chooses Temple Product Video Generator.

The entry point makes one action clear:

```text
Create a new product video.
```

The user should immediately understand that this product turns product information, product photos, and a Chinese description into a short video draft.

## 2. Home Screen Actions

On the Temple Product Video Generator home screen, the user can:

- Start a new product video
- Continue a recent draft
- Review previous exports
- Open saved product materials

For V1, the main action is Start New Product Video.

When the user starts a new project, the system creates a draft workspace for that video.

The user does not need to understand folders, metadata, providers, or AI model names at this stage.

## 3. Selecting the Product

The user selects or creates the product being promoted.

If the product already exists, the user chooses it from the Product Library.

If the product does not exist yet, the user enters:

- Product name
- Product category
- Short product description
- Main selling point

Example:

```text
Product name: Temple Energy Candle
Product category: Candle
Short product description: A handmade candle designed for meditation, calm, and daily ritual.
Main selling point: Helps create a focused and peaceful ritual space.
```

After this step, the user should feel that the product identity is clear enough for AI to generate a focused video.

## 4. Providing Photos / Materials

The user adds the product materials.

Required material:

- At least one product photo

Optional materials:

- Additional product photos
- Brand image
- Packaging photo
- Reference video
- Logo
- Existing product description
- Preferred visual style reference

The user should be able to mark one image as the main product image.

The main product image is treated as the primary visual reference for the video.

The user should see a simple confirmation that the product photo is ready.

The user should not need to manually name files or place them into folders.

## 5. Entering the Chinese Description

The user enters a Chinese description of what the video should communicate.

The description can be short and natural.

Example:

```text
請幫我做一支短影片，介紹這款蠟燭適合在晚上冥想、靜心、整理情緒時使用。感覺要溫柔、乾淨、有儀式感，不要太商業。
```

The user may also choose:

- Target platform
- Tone
- Video length
- Call to action

Recommended V1 defaults:

- Language: Traditional Chinese
- Format: Vertical 9:16
- Length: 15 to 30 seconds
- Tone: calm, clear, premium
- Target platform: Instagram Reels / TikTok / YouTube Shorts / Shorts

The system should confirm the user intent in plain language before generation.

Example confirmation:

```text
這支影片會介紹 Temple Energy Candle，主軸是晚上冥想與靜心使用。影片風格會偏溫柔、乾淨、有儀式感，輸出為 9:16 短影片。
```

## 6. AI Generation Steps

After the user confirms, AI begins preparing the video.

From the user's perspective, generation has clear stages:

1. Understand Product
2. Create Video Concept
3. Create Scene Plan
4. Create Visual Direction
5. Prepare Voiceover and Subtitles
6. Generate Preview

The user should see normal-language progress, not technical model output.

## 7. Progress Feedback

Progress states should include:

- Reading product details
- Checking product photos
- Understanding Chinese description
- Writing video concept
- Creating scene plan
- Preparing Chinese voiceover
- Preparing subtitles
- Preparing visual direction
- Creating preview
- Saving draft
- Ready for review

If a step takes longer than expected, the user should see which step is still running.

The user should not see low-level technical messages unless action is required.

## 8. Preview Experience

When the preview is ready, the user reviews the video draft.

The preview page should show:

- The video preview
- Product name
- Target platform
- Video length
- Scene list
- Voiceover text
- Subtitle text
- Caption draft
- Thumbnail suggestion
- Review status

The user can:

- Approve the preview
- Edit text
- Regenerate one scene
- Reject the draft
- Save and continue later

The user should not be forced to regenerate the entire video if only one scene is weak.

## 9. Regenerating a Single Scene

If one scene is not good enough, the user selects that scene and chooses regenerate.

The user explains the issue in plain Chinese.

Examples:

```text
這一段太商業，請改得更安靜自然。
```

```text
畫面沒有突出蠟燭，請讓產品更清楚。
```

```text
字幕太長，請縮短。
```

The system regenerates only the selected scene's affected parts:

- Visual direction
- Scene text
- Voiceover line
- Subtitle line
- Preview clip when available

The rest of the video remains unchanged unless the user chooses full regeneration.

After regeneration, the user compares the updated scene with the previous version.

The user can keep the new version or restore the previous version.

## 10. Export Process

When the user approves the preview, they choose export.

The export process asks for:

- Platform
- Final video name
- Whether to include subtitles
- Whether to export caption text

Default export:

- Vertical 9:16 MP4
- Traditional Chinese subtitles
- Caption text
- Metadata record

Supported V1 export targets:

- Instagram Reels
- TikTok
- YouTube Shorts
- Shorts

After export, the user sees:

- Final video location
- Caption location
- Metadata location
- Export status

The product does not automatically publish to social platforms in V1.

## 11. Error Handling

Errors should be written in plain language with a clear next action.

### Missing Product Photo

Message:

```text
請先加入至少一張產品照片，才能建立影片。
```

User action:

Upload or select a product photo.

### Description Too Short

Message:

```text
目前描述太短，AI 可能無法抓到影片重點。請補充產品用途、風格或主要賣點。
```

User action:

Add more detail or continue with a basic draft.

### Preview Generation Failed

Message:

```text
影片預覽建立失敗。你的文字和素材已保留，可以重新產生預覽。
```

User action:

Retry preview generation.

### Export Failed

Message:

```text
影片匯出失敗。草稿已保存，請重新匯出。
```

User action:

Retry export or choose a different output setting.

### Material Cannot Be Read

Message:

```text
其中一個素材無法讀取。請重新上傳或改用其他檔案。
```

User action:

Replace the material.

### AI Output Is Not Good Enough

Message:

```text
你可以只重生不滿意的場景，不需要重新建立整支影片。
```

User action:

Select the weak scene and regenerate it.

## 12. Recovery Flow

The product should protect the user's work.

If the user closes the product, refreshes the page, or generation fails, the draft should remain recoverable.

The user can return to:

- Product details
- Uploaded materials
- Chinese description
- Scene plan
- Generated text
- Preview if available
- Export records if completed

Recovery entry points:

- Continue recent draft
- Open previous project
- Retry failed generation
- Retry failed export

When recovering a failed project, the user should see the last completed step.

Example:

```text
上次已完成場景規劃，但影片預覽建立失敗。你可以繼續產生預覽。
```

The user should never need to re-enter everything after a failure.

## 13. Definition of Done

One Temple product video task is done when:

1. The product is selected or created.
2. At least one product photo is provided.
3. The user enters a Chinese product video description.
4. AI creates a video concept.
5. AI creates a scene plan.
6. AI prepares Chinese voiceover text.
7. AI prepares subtitle text.
8. AI prepares a caption draft.
9. A preview is available for review.
10. The user can approve, reject, or regenerate one scene.
11. The user approves the final preview.
12. The final MP4 is exported.
13. Caption text is saved.
14. Metadata is saved.
15. The export location is shown to the user.

The completed result should be understandable, reviewable, and ready for manual posting.
