# Temple Product Video Generator V1

Temple Product Video Generator 是 Temple AI Studio 的第一個可日常使用產品。

V1 使用本機流程，不會自動呼叫付費 API。系統會使用商品資料、商品照片、中文描述、內容模型與 FFmpeg 建立 9:16 MP4 影片和完整交付包。ComfyUI、Whisper、TTS 在 V1 中屬於可設定的未來整合項目；沒有連線時會使用本機備援流程。

## 啟動

開發版本：

```text
start.bat
```

或：

```powershell
python server.py
```

瀏覽器網址：

```text
http://127.0.0.1:4173
```

正式安裝版請使用：

```text
D:\AI\Temple AI Studio\start_temple_ai_studio.bat
```

## 一鍵測試

```powershell
python server.py --smoke-test
```

測試會建立示範商品、商品照片、影片專案、場景、字幕、預覽影片、核准狀態與 MP4 輸出包。

## 需要的本機工具

必要：

- Python 3
- Pillow
- FFmpeg

目前偵測到的 FFmpeg 路徑：

```text
C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe
```

如果 FFmpeg 不可用，系統仍可建立商品資料、場景、字幕、文案、生成提示詞與 metadata，但無法輸出 MP4。

可選：

- ComfyUI
- Whisper
- 本機 TTS

## 操作流程

1. 商品影片：建立或選擇商品，並上傳至少一張照片或 Logo。
2. 純文字影片：在「建立影片」選擇純文字模式，不需要商品或照片。
3. 輸入繁體中文需求、平台與影片秒數。
4. 按「送出並開始製作」後立即取得工作編號。
5. 在「生成進度」查看後端即時進度、目前階段、時間、Provider 與錯誤處理。
6. 工作完成後播放預覽、檢查場景、核准影片並建立完整交付包。

工作狀態會保存到正式資料庫；重新整理瀏覽器或重啟程式後，未完成工作會自動恢復。

## 輸出內容

每個影片專案會輸出：

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

輸出位置：

```text
data\exports\<project-id>\
```

正式安裝版輸出位置：

```text
D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\exports\
```

## 資料位置

開發版本資料：

```text
apps\temple-product-video-generator\data\
```

正式安裝版資料：

```text
D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\
```

商品資料庫：

```text
D:\AI\Temple AI Studio Production Data\applications\temple-product-video-generator\database.json
```

`data`、`runtime`、`release`、logs、exports 與快取檔案不納入 Git。

## 備份與還原

「設定」頁提供：

- 建立資料備份
- 還原備份 zip
- 建立畫面證據
- 建立發行包
- 建立支援包

還原備份時必須輸入：

```text
RESTORE
```

系統會先建立還原前安全備份，再執行還原。

## 支援包

在「設定」頁點擊：

```text
建立支援包
```

支援包輸出到：

```text
data\support\
```

支援包只包含版本資訊、工具狀態、已遮蔽敏感資訊的設定摘要與 logs。支援包不包含 API key、token、密碼、商品照片、生成影片、資料庫、生成提示詞、字幕、旁白或客戶敏感輸出。

## ComfyUI

ComfyUI 是 V1 的未來可替換 provider。

目前可在「設定」頁填寫：

- ComfyUI 連線網址
- ComfyUI 工作流程

沒有 ComfyUI 時，V1 會使用本機備援：

```text
商品照片 + 場景文字 + Ken Burns 動態 + 字幕 + FFmpeg MP4
```

## 安全原則

刪除操作只移除應用內記錄，不會自動刪除正式安裝資料夾外的使用者檔案。

不要手動刪除：

```text
data\
```

此資料夾包含商品、照片、專案、輸出、備份與操作證據。
