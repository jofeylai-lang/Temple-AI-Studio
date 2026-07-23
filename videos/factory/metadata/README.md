# 影片 Metadata 規格

每支影片都應有一份 metadata。

## 建議檔名

```text
YYYYMMDD_HHMMSS_video-factory_task-id.metadata.md
```

## 建議欄位

```text
# Video Metadata

task_id:
created_at:
source_input:
title:
platforms:
duration:
aspect_ratio:
script_file:
storyboard_file:
image_assets:
narration_file:
subtitle_file:
render_file:
shorts_output:
youtube_output:
tiktok_output:
instagram_output:
status:
quality_score:
notes:
```

## 狀態建議

- `draft`
- `script-ready`
- `assets-ready`
- `voice-ready`
- `subtitle-ready`
- `rendered`
- `exported`
- `published`
- `failed`
