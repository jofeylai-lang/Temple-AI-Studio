# videos/factory

AI 影片工廠的影片專案、字幕、渲染、輸出與 metadata 集中放在這裡。

## 子資料夾

- `projects/`：每支影片的專案資料
- `renders/`：影片渲染草稿與中間版本
- `subtitles/`：字幕檔
- `metadata/`：影片 metadata
- `exports/`：平台輸出版本

## 建議專案資料夾格式

```text
videos/factory/projects/YYYY/MM/DD/vf-000001/
```

每個影片專案可包含：

```text
brief.md
storyboard.md
assets.md
edit-notes.md
metadata.md
```

## 輸出位置

```text
videos/factory/exports/shorts/YYYY/MM/DD/
videos/factory/exports/youtube/YYYY/MM/DD/
videos/factory/exports/tiktok/YYYY/MM/DD/
videos/factory/exports/instagram/YYYY/MM/DD/
```

## 命名規則

```text
YYYYMMDD_HHMMSS_video-factory_task-id_platform_v01.mp4
```

範例：

```text
20260709_104000_video-factory_vf-000001_shorts_v01.mp4
20260709_104000_video-factory_vf-000001_youtube_v01.mp4
20260709_104000_video-factory_vf-000001_tiktok_v01.mp4
20260709_104000_video-factory_vf-000001_instagram_v01.mp4
```
