# AI 影片工廠工作流

## 工作流總覽

```text
1. 接收一句話
2. 建立任務 ID
3. 判斷影片目的與平台
4. 生成影片腳本
5. 生成分鏡表
6. 為每個分鏡生成圖片 Prompt
7. 生成或收集圖片素材
8. 生成旁白稿
9. 生成旁白音檔
10. 生成字幕
11. 組合影片
12. 輸出平台版本
13. 建立 metadata
14. 建立品質檢查紀錄
```

## 任務 ID

建議格式：

```text
vf-000001
```

其中 `vf` 代表 video factory。

## 日期分類

所有任務都依日期分類：

```text
YYYY/MM/DD/
```

## 製作階段

### 1. 一句話輸入

保留使用者原始輸入，不覆蓋、不改寫。

### 2. 腳本生成

腳本應包含：

- 標題
- Hook
- 主要內容
- 結尾
- 行動呼籲
- 旁白稿
- 分鏡

### 3. 圖片生成

每個分鏡至少對應一個圖片 Prompt。

圖片素材可連結到：

```text
images/factory/generated/YYYY/MM/DD/
```

或影片專案自己的素材資料夾。

### 4. 旁白生成

旁白稿先放在 `scripts/video-factory/`，旁白音檔放在 `voice/factory/narration/`。

### 5. 字幕生成

字幕檔放在：

```text
videos/factory/subtitles/YYYY/MM/DD/
```

建議格式：

- `.srt`
- `.vtt`
- `.txt`

### 6. 影片生成

影片草稿與渲染檔放在：

```text
videos/factory/renders/YYYY/MM/DD/
```

### 7. 平台輸出

```text
videos/factory/exports/shorts/YYYY/MM/DD/
videos/factory/exports/youtube/YYYY/MM/DD/
videos/factory/exports/tiktok/YYYY/MM/DD/
videos/factory/exports/instagram/YYYY/MM/DD/
```

## 失敗處理

每個階段失敗都應記錄：

- 任務 ID
- 失敗階段
- 原始輸入
- 錯誤原因
- 是否可重試
- 下一步建議
