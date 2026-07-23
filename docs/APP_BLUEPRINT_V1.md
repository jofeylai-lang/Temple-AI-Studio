# App Blueprint V1

Application: Temple Product Video Generator

Platform: Temple AI Studio

Date: 2026-07-23

Status: V1 Ready Candidate

## Purpose

This document defines the application structure for Temple Product Video Generator before UI design and technical implementation.

It is intended to let a designer and an engineer understand the same product without ambiguity.

This document does not define code, APIs, UI graphics, visual appearance, or wireframes.

## Source of Truth References

This blueprint follows:

- `AUDIT_REPORT.md`
- `NEW_ROADMAP.md`
- `PRODUCT_SPEC_V1.md`
- `USER_JOURNEY_V1.md`
- `CONTENT_MODEL_V1.md`
- `AI_REASONING_PIPELINE_V1.md`

The application scope is limited to V1: one Temple product video workflow, manual review, vertical export preparation, metadata, caption, subtitles, scene-level regeneration, and recovery from failed or unfinished work.

## 1. Overall Application Structure

Temple Product Video Generator is the first application built on top of Temple AI Studio.

The application should help the user create one Temple product video from product selection to final MP4 export.

The application should feel like a focused production workspace, not a general AI playground.

### Main Modules

#### Home

Purpose:

Start a new product video, resume unfinished work, or open recent projects.

#### Product Library

Purpose:

Store and manage Temple products used for video generation.

#### Create Video

Purpose:

Collect the product, photos/materials, Chinese description, target platform, tone, and video length.

#### Generation Progress

Purpose:

Show what AI is currently preparing and preserve user confidence during generation.

#### Preview

Purpose:

Review the generated video draft, scene structure, narration, subtitles, caption, and metadata.

#### Export

Purpose:

Prepare and confirm the final MP4 export package.

#### Settings

Purpose:

Manage default language, preferred platform, brand defaults, generation preferences, and export defaults.

### Navigation

Primary navigation should include:

- Home
- Product Library
- Create Video
- Previous Projects
- Settings

Contextual navigation should include:

- Back to product selection
- Back to edit description
- Go to generation progress
- Go to preview
- Go to export
- Return to unfinished draft

The user should always understand where they are in the video creation process.

### Entry Points

Primary entry points:

- Start New Product Video
- Continue Recent Draft
- Open Product Library
- Open Previous Export

Secondary entry points:

- Duplicate a previous video project
- Create video from an existing product
- Retry a failed generation
- Resume a paused generation

## 2. Screen Inventory

The V1 application contains these screens:

1. Home
2. Product Library
3. Product Detail
4. Create Video
5. Generation Progress
6. Preview
7. Scene Detail
8. Export
9. Previous Projects
10. Settings

The required screens from the product request are:

- Home
- Product Library
- Create Video
- Generation Progress
- Preview
- Export
- Settings

Product Detail, Scene Detail, and Previous Projects are included because they remove ambiguity from edit, regeneration, and recovery flows.

## 3. Each Screen

### 3.1 Home

Purpose:

The Home screen is the starting point for the application.

It should help the user begin or continue product video work immediately.

Information displayed:

- Main action: Start New Product Video
- Recent unfinished drafts
- Recent exported videos
- Quick access to Product Library
- Generation or export failures that need attention

User actions:

- Start a new product video
- Continue a draft
- Open a previous export
- Open Product Library
- Open Settings

Navigation to other screens:

- Start New Product Video -> Create Video
- Continue Draft -> Create Video, Generation Progress, or Preview depending on last saved step
- Open Product Library -> Product Library
- Open Previous Export -> Previous Projects or Export
- Open Settings -> Settings

### 3.2 Product Library

Purpose:

The Product Library stores products that can be used to generate Temple product videos.

Information displayed:

- Product list
- Product name
- Product category
- Main product image
- Short description
- Last used date
- Draft or video count per product

User actions:

- Select a product
- Create a new product
- Search products
- Open product details
- Start video from selected product

Navigation to other screens:

- Select Product -> Product Detail
- Start Video -> Create Video
- Create New Product -> Product Detail
- Back -> Home

### 3.3 Product Detail

Purpose:

The Product Detail screen lets the user review or edit product information before video generation.

Information displayed:

- Product name
- Product category
- Product description
- Main selling point
- Product photos/materials
- Brand notes
- Previous videos for this product

User actions:

- Edit product name
- Edit product description
- Edit selling point
- Add or remove product photos/materials
- Set main product image
- Start a new video with this product
- Return to Product Library

Navigation to other screens:

- Start Video -> Create Video
- Save Product -> Product Library
- Back -> Product Library

### 3.4 Create Video

Purpose:

The Create Video screen collects all information required to generate a video.

Information displayed:

- Selected product
- Main product image
- Product materials
- Chinese video description field
- Target platform
- Video length
- Tone
- Call to action
- Generation readiness status

User actions:

- Select or change product
- Add or change product photo
- Enter Chinese description
- Select platform
- Select tone
- Select video length
- Enter CTA
- Save draft
- Start generation

Navigation to other screens:

- Change Product -> Product Library
- Edit Product -> Product Detail
- Start Generation -> Generation Progress
- Save Draft -> Home or Previous Projects
- Back -> Home

### 3.5 Generation Progress

Purpose:

The Generation Progress screen shows the user what AI is doing.

It should reduce uncertainty during longer generation steps.

Information displayed:

- Current generation stage
- Completed stages
- Pending stages
- Product name
- Target platform
- Estimated current progress
- Any warnings or missing optional information

Progress stages:

- Reading product details
- Checking product photos
- Understanding Chinese description
- Planning video story
- Planning scenes
- Preparing narration
- Preparing subtitles
- Preparing visual direction
- Creating preview
- Saving draft

User actions:

- Cancel generation
- Pause or leave and return later
- Retry if failed
- View preserved draft information after failure

Navigation to other screens:

- Completed -> Preview
- Cancel -> Create Video or Home
- Failed -> Recovery option, Create Video, or Retry
- Leave and return later -> Home

### 3.6 Preview

Purpose:

The Preview screen lets the user review the generated video draft before export.

Information displayed:

- Video preview
- Product name
- Target platform
- Video length
- Scene list
- Narration text
- Subtitle text
- Caption draft
- Thumbnail suggestion
- Metadata summary
- Review status

User actions:

- Play preview
- Approve preview
- Reject preview
- Edit text
- Open a scene
- Regenerate one scene
- Regenerate full video
- Save draft
- Proceed to export

Navigation to other screens:

- Open Scene -> Scene Detail
- Regenerate Scene -> Generation Progress or Scene Detail
- Regenerate Full Video -> Generation Progress
- Approve and Export -> Export
- Back -> Create Video
- Save and Exit -> Home

### 3.7 Scene Detail

Purpose:

The Scene Detail screen lets the user inspect and revise one scene without affecting the full video.

Information displayed:

- Scene number
- Scene purpose
- Estimated duration
- Visual description
- Narration
- Subtitle
- Prompt summary
- Music direction
- Transition direction
- Optional effects
- Current scene version
- Previous version if available

User actions:

- Edit narration
- Edit subtitle
- Edit scene note
- Regenerate this scene
- Keep new version
- Restore previous version
- Return to Preview

Navigation to other screens:

- Regenerate Scene -> Generation Progress
- Keep Version -> Preview
- Restore Previous -> Preview
- Back -> Preview

### 3.8 Export

Purpose:

The Export screen prepares the approved video package.

Information displayed:

- Approved video preview
- Selected platform
- Export format
- Subtitle inclusion option
- Caption text
- Thumbnail suggestion
- Metadata summary
- Final file name
- Export status

User actions:

- Confirm platform
- Confirm final video name
- Include or exclude subtitles
- Export MP4
- Copy caption
- Open export location
- Return to Preview

Navigation to other screens:

- Export Complete -> Export result state
- Back -> Preview
- Open Project -> Previous Projects
- Return Home -> Home

### 3.9 Previous Projects

Purpose:

Previous Projects gives the user access to drafts, approved videos, exported videos, and failed projects.

Information displayed:

- Project list
- Product name
- Created date
- Status
- Target platform
- Last completed step
- Export location when available

User actions:

- Open draft
- Resume unfinished work
- Open exported project
- Duplicate a project
- Retry failed generation

Navigation to other screens:

- Open Draft -> Create Video, Generation Progress, or Preview
- Open Exported Project -> Export
- Retry Failed -> Generation Progress
- Back -> Home

### 3.10 Settings

Purpose:

Settings manages product video defaults.

Information displayed:

- Default language
- Default target platform
- Default video length
- Default tone
- Brand defaults
- Export defaults
- Local/cloud generation preference at a non-technical level

User actions:

- Change default language
- Change default platform
- Change default tone
- Change default video length
- Set export preferences
- Return to previous screen

Navigation to other screens:

- Save Settings -> Home or previous screen
- Back -> Home or previous screen

## 4. Primary User Flow

This is the normal workflow from launching the app to exporting an MP4.

1. User opens Temple Product Video Generator.
2. User lands on Home.
3. User selects Start New Product Video.
4. User arrives at Create Video.
5. User selects an existing product or creates a new one.
6. User confirms product name, description, selling point, and main image.
7. User enters a Chinese video description.
8. User selects target platform.
9. User selects video length and tone, or accepts defaults.
10. User starts generation.
11. User sees Generation Progress.
12. AI prepares product understanding, story, scenes, narration, subtitles, visual direction, caption, and preview.
13. When generation completes, user moves to Preview.
14. User watches the preview.
15. User reviews scene list, narration, subtitles, caption, and thumbnail suggestion.
16. User approves the preview or revises weak parts.
17. User proceeds to Export.
18. User confirms final platform, subtitle inclusion, caption, and file name.
19. User exports MP4.
20. User sees export result, caption, metadata status, and final location.

The primary flow is complete when the final MP4 and supporting export package are available for manual posting.

## 5. Secondary Flows

### 5.1 Edit Product

Trigger:

The user notices product information is missing, outdated, or incorrect.

Flow:

1. User opens Product Library or Product Detail.
2. User edits product name, description, selling point, photos, or brand notes.
3. User saves the product.
4. User returns to Create Video or Product Library.

Expected result:

The updated product information is used for future video generation.

### 5.2 Regenerate One Scene

Trigger:

The preview is mostly acceptable, but one scene is weak.

Flow:

1. User opens Preview.
2. User selects the weak scene.
3. User opens Scene Detail.
4. User explains what should change.
5. User chooses Regenerate This Scene.
6. System regenerates only the selected scene's affected content.
7. User compares the new version with the previous version.
8. User keeps the new version or restores the previous version.
9. User returns to Preview.

Expected result:

Only one scene changes. The approved parts of the video remain stable.

### 5.3 Retry Failed Generation

Trigger:

Generation fails before preview is created.

Flow:

1. User sees a failure message on Generation Progress.
2. User sees which step failed.
3. User sees what was preserved.
4. User selects Retry.
5. System retries from the nearest recoverable step.
6. If retry succeeds, user proceeds to Preview.

Expected result:

The user does not need to restart the entire project.

### 5.4 Cancel Generation

Trigger:

User decides to stop generation while it is running.

Flow:

1. User selects Cancel Generation.
2. App explains that current generated results may be incomplete.
3. User confirms cancellation.
4. App saves the draft state.
5. User returns to Create Video or Home.

Expected result:

The project is preserved as an unfinished draft.

### 5.5 Resume Unfinished Work

Trigger:

User returns to a draft after leaving, canceling, or encountering a failure.

Flow:

1. User opens Home or Previous Projects.
2. User selects an unfinished draft.
3. App shows the last completed step.
4. User resumes from Create Video, Generation Progress, or Preview.

Expected result:

The user continues from the nearest useful point without re-entering all information.

## 6. Data Flow

This section describes high-level information movement between screens. It does not define implementation details.

### Home to Create Video

Information passed:

- New project intent
- Draft project selection if continuing

### Product Library to Create Video

Information passed:

- Selected product
- Product name
- Product category
- Product description
- Main selling point
- Main product image
- Product materials

### Product Detail to Create Video

Information passed:

- Updated product information
- Updated product materials
- Main product image selection

### Create Video to Generation Progress

Information passed:

- Product information
- Product materials
- Chinese video description
- Target platform
- Tone
- Video length
- CTA
- Draft project identity

### Generation Progress to Preview

Information passed:

- Video concept
- Scene plan
- Narration
- Subtitles
- Visual directions
- Caption draft
- Thumbnail suggestion
- Preview media when available
- Metadata summary

### Preview to Scene Detail

Information passed:

- Selected scene
- Scene content
- Scene version history when available
- User revision request if provided

### Scene Detail to Preview

Information passed:

- Updated scene content
- Current scene version
- Regeneration status

### Preview to Export

Information passed:

- Approved preview
- Final scene list
- Final narration
- Final subtitles
- Caption
- Thumbnail suggestion
- Metadata
- Target platform

### Export to Previous Projects

Information passed:

- Final export status
- Final MP4 location
- Caption location
- Metadata location
- Project status

## 7. Definition of Done

The App Blueprint V1 is complete when it clearly defines:

1. Main application modules.
2. Primary navigation.
3. Entry points.
4. Complete screen inventory.
5. Purpose of every screen.
6. Information displayed on every screen.
7. User actions on every screen.
8. Navigation from every screen.
9. Primary user flow from launch to MP4 export.
10. Secondary flows for product editing, single-scene regeneration, retry, cancel, and resume.
11. High-level data flow between screens.
12. Clear boundaries excluding code, UI graphics, APIs, implementation details, and wireframes.

The product blueprint is approved only when a designer and an engineer can use it to build the same application behavior without needing to reinterpret the product intent.

## Stop Point

This document defines the application blueprint only.

No implementation should begin until this blueprint is reviewed and approved.
