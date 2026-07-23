# Cloud Video Platform Handoff Pack

Project ID: vf-cloud-platform-0001
Date: 2026-07-09

## Goal

Use professional cloud image-to-video platforms to generate a more realistic full-body human video from the prepared full-body reference image.

## Why This Exists

The local SVD test produced motion, but the quality was not good enough for realistic human full-body movement.

Professional platforms such as Kling, Runway, Luma, Hailuo, and PixVerse usually produce better body motion, camera motion, and cinematic realism, but they require login, credits, or API access.

## Inputs

- `inputs/source-face-reference.jpg`：原始自拍參考
- `inputs/full-body-reference.png`：全身角色基準圖，建議作為主要 image-to-video 輸入
- `inputs/face-motion-reference.mp4`：臉部微動參考，可作為風格/表情參考

## Recommended Platform Order

1. Kling：優先測試，適合 image-to-video 與 motion control。
2. Runway：適合高質感真人/電影感，但通常需要帳號與點數。
3. Luma：適合鏡頭感、自然運鏡、形象影片。
4. Hailuo：適合短影音快速測試。
5. PixVerse：適合社群短影音與快速多版本。

## Manual Requirement

You must log in to the selected platform and provide credits/API access if required.

Codex can prepare prompts, assets, metadata, and workflow notes, but cannot bypass paid credits, login, CAPTCHA, or platform account verification.

