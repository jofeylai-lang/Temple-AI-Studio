# AI 圖片工廠工作流

## 工作流總覽

```text
1. 接收一句話
2. 建立任務 ID
3. 分析用途與風格
4. 生成正式 Prompt
5. 送出圖片生成任務
6. 接收圖片結果
7. 建立日期資料夾
8. 儲存圖片
9. 產生 metadata
10. 建立 Prompt 紀錄
11. 建立結果摘要
```

## 建議流程

### 1. 接收輸入

保留使用者原始輸入，不覆蓋、不改寫。

### 2. Prompt 整理

將一句話整理成可重複使用的圖片 Prompt，並補上：

- 主體
- 場景
- 風格
- 構圖
- 光線
- 色彩
- 品質描述
- 負面提示詞

### 3. 圖片生成

第一階段先只規劃，不指定模型。

未來可接：

- OpenAI 圖片模型
- Stable Diffusion
- ComfyUI
- Midjourney 工作流
- 其他本地或雲端圖片模型

### 4. 儲存圖片

圖片依日期分類：

```text
images/factory/generated/YYYY/MM/DD/
```

### 5. 建立 metadata

metadata 依日期分類：

```text
images/factory/metadata/YYYY/MM/DD/
```

### 6. 建立 Prompt 紀錄

Prompt 紀錄依日期分類：

```text
prompts/image-factory/YYYY/MM/DD/
```

## 失敗處理

每次失敗仍應保留：

- 原始輸入
- 任務 ID
- 失敗階段
- 錯誤原因
- 是否可重試
- 建議修正方式

