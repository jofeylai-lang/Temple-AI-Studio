# Image Factory V1

Image Factory V1 是 Jofey AI Studio 的第一個功能模組。

目標是建立一個「一句話生成圖片」的系統架構。此版本不串接任何付費 API，也不真正生成圖片，先完成可擴充、可替換、可追蹤的系統設計。

## 核心流程

```text
一句話
↓
讀取 Prompt 設定
↓
選擇 Provider
↓
建立生成任務
↓
未來呼叫圖片模型
↓
依日期建立 output 資料夾
↓
儲存圖片
↓
建立 metadata.json
↓
寫入 logs
```

## 模組結構

```text
image_factory/
├─ README.md
├─ config/        模組設定與 Provider 設定
├─ providers/     可替換的圖片生成 Provider 設計
├─ prompts/       集中管理所有 Prompt
├─ output/        圖片輸出區，依日期分類
├─ metadata/      metadata 規格與範本
└─ logs/          任務紀錄、錯誤紀錄與執行紀錄
```

## Provider 支援規劃

每個 Provider 都要設計成可替換模組，未來可依需求切換：

- OpenAI Images
- FLUX
- Stable Diffusion
- ComfyUI
- Google Imagen

## 日期輸出規則

所有生成結果都依日期分類：

```text
output/
└─ YYYY/
   └─ MM/
      └─ DD/
```

範例：

```text
output/
└─ 2026/
   └─ 07/
      └─ 09/
```

每張圖片都應有一份同名 metadata：

```text
20260709_103000_if-000001_v01.png
20260709_103000_if-000001_v01.metadata.json
```

## Metadata 必要欄位

每張圖片必須記錄：

- `prompt`
- `negative_prompt`
- `model`
- `seed`
- `size`
- `created_at`
- `provider`

完整格式見：

- [metadata/schema.md](metadata/schema.md)
- [metadata/metadata.template.json](metadata/metadata.template.json)

## V1 不做的事

- 不串接付費 API
- 不真正生成圖片
- 不建立網站介面
- 不建立 Telegram Bot
- 不做自動部署
- 不保存 API Key

## V1 完成標準

- 資料夾結構完成
- Provider 可替換設計完成
- Prompt 集中管理規則完成
- 日期輸出規則完成
- metadata 規格完成
- logs 規則完成

