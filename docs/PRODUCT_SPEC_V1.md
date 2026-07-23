# Product Spec V1

Product: Temple Product Video Generator

Platform: Temple AI Studio

Date: 2026-07-23

Status: V1 Ready Candidate

## 1. Product Vision

Temple Product Video Generator is the first usable product built on top of Temple AI Studio.

The product helps a user turn a simple product idea, product image, or selling point into a short social-ready product video.

Temple AI Studio remains the operating system. Temple Product Video Generator is only the first application running on top of it.

The goal is not to build every AI capability at once. The goal is to create one repeatable daily workflow that can produce useful marketing videos with clear inputs, clear outputs, traceable metadata, and a human review step.

The first version should prove that Temple AI Studio can support practical business content production.

## 2. Target User

The primary user is a solo creator, small business owner, brand operator, or content producer who needs short product videos frequently but does not want to manually plan every script, prompt, caption, subtitle, and export format.

The user may not be technical. The workflow should feel like filling in a brief, reviewing generated assets, and choosing what to export.

The first target user likely needs:

- Product promotion videos
- Social media clips
- Short product explainers
- Reels / Shorts / TikTok-ready assets
- Repeatable output without rebuilding the workflow each time

## 3. Daily Workflow

The intended daily workflow:

1. User opens Temple Product Video Generator.
2. User enters a short product description.
3. User adds or selects one product image.
4. User selects target platform: Shorts, Instagram Reels, TikTok, or YouTube Shorts.
5. User enters the main selling point.
6. System generates a structured video brief.
7. System generates or prepares:
   - script
   - visual prompt
   - voiceover text
   - subtitle text
   - metadata
   - export plan
8. User reviews the result.
9. User approves, edits, or rejects the output.
10. Final assets are saved into the correct dated project/output folders.

V1 may be semi-automated. Manual review is required before publishing.

## 4. Input

V1 input should stay minimal.

Required inputs:

- Product name
- Product description
- Main selling point
- Target platform
- Product image or image reference

Optional inputs:

- Tone: premium, friendly, educational, energetic, elegant, direct
- Audience: general consumers, fans, members, customers, followers
- Language: Traditional Chinese by default
- Video length target: 15 seconds, 30 seconds, or 45 seconds
- Call to action
- Brand notes

Input rules:

- The product image should be treated as the main visual reference.
- The product name should appear in metadata.
- The selling point should drive the script.
- Target platform should determine export ratio and caption style.
- User approval is required before final publishing.

## 5. Output

V1 output should include both creative assets and traceability records.

Required outputs:

- Video brief
- Short script
- Voiceover text
- Subtitle text
- Visual prompt
- Platform caption
- Metadata record
- Final export location

Target video output:

- Primary format: vertical 9:16
- Primary platforms:
  - Instagram Reels
  - TikTok
  - YouTube Shorts
  - Shorts

Metadata should include:

- project id
- product name
- created date
- input description
- selected platform
- script version
- prompt version
- provider used
- source image path
- output path
- review status
- notes

V1 does not need to automatically publish to platforms.

## 6. UI Layout

The UI should be simple and operational, not a marketing landing page.

Recommended first screen:

- Left panel: product input form
- Center panel: generated brief and script preview
- Right panel: output checklist and export status
- Bottom area: review actions

Core sections:

### Product Input

Fields:

- Product name
- Product description
- Selling point
- Target platform
- Tone
- Upload/select product image

### Generated Plan

Displays:

- Video concept
- Script
- Voiceover
- Subtitle text
- Visual prompt
- Caption

### Output Preview

Displays:

- Selected platform format
- Expected ratio
- Duration target
- Source image used
- Output status

### Review Controls

Actions:

- Approve
- Request revision
- Mark rejected
- Export

V1 UI should prioritize clarity and repeatability over visual decoration.

## 7. Must Have

V1 must have:

- A clear product input flow
- One repeatable product video workflow
- One primary vertical export target
- Product-specific prompt generation
- Script generation
- Subtitle text generation
- Caption generation
- Metadata generation
- Dated output organization
- Human review before final approval
- Clear distinction between draft and final output
- Reuse of existing Temple AI Studio folders where possible

V1 must preserve:

- Prompt traceability
- Source image traceability
- Provider traceability
- Output traceability
- Review status

V1 should be designed for repeat daily use, not one-off demos.

## 8. Out of Scope

The following are out of scope for V1:

- Building a universal AI video engine
- Supporting every image/video provider
- Automatic publishing to TikTok, Instagram, YouTube, or Telegram
- Fully automated paid API usage
- User accounts
- Billing
- Team permissions
- Advanced video editing timeline
- Full-body human animation
- Character lip-sync
- Voice cloning
- Custom model training
- Multi-language campaign generation
- Large-scale batch generation
- Analytics dashboard
- Website redesign
- Telegram bot implementation
- Refactoring existing project architecture

V1 should not depend on solving every AI capability.

## 9. Acceptance Criteria

Temple Product Video Generator V1 is acceptable when the following are true:

1. A user can provide a product name, description, selling point, target platform, and product image.
2. The product can generate a usable video brief.
3. The product can generate a short script suitable for a vertical product video.
4. The product can generate voiceover text.
5. The product can generate subtitle text.
6. The product can generate a platform caption.
7. The product can produce or prepare a vertical 9:16 output path.
8. Every generated project has metadata.
9. Every output is saved under a dated folder.
10. Draft and final outputs are clearly distinguishable.
11. The workflow can be repeated for at least three different products.
12. A human can approve or reject the generated result.
13. The product does not require new architecture to validate the first workflow.
14. The product can be evaluated using a simple quality checklist.

Minimum validation test:

- Create three sample product video projects.
- Confirm each project has input, script, subtitle, caption, metadata, and output records.
- Confirm the final output is understandable and usable for social media review.

## Approval Gate

No implementation should begin until this product spec is reviewed and approved.
