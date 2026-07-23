# Temple Product Video Generator V1

Temple Product Video Generator 是 Temple AI Studio 的第一個可實際使用產品。

V1 採用本機優先，不呼叫付費 API，不需要 GitHub CLI。即使沒有 ComfyUI、Whisper 或 TTS，也可以使用商品照片、繁體中文內容模板與 FFmpeg 產生可播放的 9:16 MP4。

## 啟動方式

雙擊：

```text
start.bat
```

或執行：

```powershell
cd "D:\AI\Jofey AI Studio\apps\temple-product-video-generator"
python server.py
```

啟動後開啟：

```text
http://127.0.0.1:4173
```

使用期間請保留啟動視窗開啟。

## 一鍵驗證

```powershell
cd "D:\AI\Jofey AI Studio\apps\temple-product-video-generator"
python server.py --smoke-test
```

驗證會建立示範商品、建立影片專案、重生一個場景、批准專案、輸出 MP4，並檢查完整內容包。

## 本機需求

必要：

- Python 3
- Pillow
- FFmpeg

本機驗收時偵測到的 FFmpeg：

```text
C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe
```

若 FFmpeg 不存在，系統仍能保存商品、照片、腳本、場景、字幕、Prompt 與 Metadata，但不會假裝輸出 MP4。

選用：

- ComfyUI
- Whisper
- 本機 TTS

## 使用流程

1. 進入「商品資料庫」。
2. 建立或選擇商品。
3. 上傳一張或多張商品照片。
4. 需要時排序、替換或移除照片。
5. 進入「建立影片」。
6. 輸入繁體中文影片需求。
7. 產生腳本、場景、旁白、字幕、Prompt、Caption、SEO、Metadata 與預覽影片。
8. 在「影片預覽」檢查整支影片。
9. 在「場景細節」編輯、批准或重生單一場景。
10. 批准整支影片。
11. 匯出完整內容包。

## 匯出內容包

每個完成專案會輸出：

- `final_video.mp4`
- `final_video_subtitled.mp4`
- `subtitles.srt`
- `narration.txt`
- `caption.txt`
- `metadata.json`
- `scenes.json`
- `prompts.json`
- `thumbnail_suggestion.txt`
- `materials_used.txt`

預設輸出位置：

```text
apps/temple-product-video-generator/data/exports/<project-id>/
```

## 資料位置

預設資料位置：

```text
apps/temple-product-video-generator/data/
```

此資料夾保存商品、照片、專案、備份與輸出檔，已被 Git 忽略，避免把私人素材或生成影片提交到版本庫。

## 備份與還原

在「設定」頁可以：

- 建立資料備份
- 還原備份 zip
- 產生操作證據圖
- 建立 release package

還原備份前必須輸入：

```text
RESTORE
```

系統會先建立安全備份，再執行還原。

## ComfyUI

ComfyUI 是 V1 選用項目。

可在「設定」頁填寫：

- ComfyUI 位址
- ComfyUI 工作流

若 ComfyUI 尚未連線，V1 會使用可靠 fallback：

```text
真實商品照片 + 場景圖片 + Ken Burns 動態 + 字幕 + FFmpeg MP4
```

## 移除方式

若要移除程式，可刪除應用程式資料夾。

請注意：刪除前請先備份 `data/`，否則商品、照片、專案和輸出影片會一起消失。
