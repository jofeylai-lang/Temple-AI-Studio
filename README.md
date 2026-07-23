# Jofey AI Studio

Jofey AI Studio 是一個面向大型 AI 內容、角色、知識庫與自動化營運的專案工作區。

目前此專案只包含資料夾與說明文件，不包含任何程式碼。

## 專案定位

此專案不只是素材倉庫，而是 AI Studio 的長期管理中心。它可以用來整理：

- AI 品牌與角色設定
- 提示詞與工作流
- 知識庫與資料來源
- 圖像、影片、聲音與 Avatar 素材
- 網站、Telegram、Instagram 與社群營運資料
- 測試、評估、輸出成品與封存紀錄

## 專業化後的資料夾結構

```text
Jofey AI Studio/
├─ strategy/      專案定位、受眾、商業方向與長期路線
├─ brand/         品牌識別、品牌語氣、視覺規範
├─ docs/          正式文件、架構、需求、決策與路線圖
├─ research/      市場研究、競品分析、靈感與未驗證想法
├─ knowledge/     AI 可使用的知識庫、資料來源、FAQ 與政策
├─ prompts/       系統提示詞、角色提示詞、工作流提示與測試
├─ models/        AI 人設、模型設定、實驗設定與版本紀錄
├─ workflows/     內容生產、審核、自動化與營運流程
├─ evaluations/   提示詞測試、品質檢查、基準評估
├─ datasets/      原始資料、整理後資料、授權資料
├─ images/        圖片素材、品牌圖片、生成圖與參考圖
├─ videos/        原始影片、剪輯版本、發布版本
├─ avatar/        AI 角色形象、外觀一致性與參考資料
├─ voice/         聲音設定、語氣規範、語音樣本與口播文字
├─ scripts/       內容腳本、影片腳本、口播稿與分鏡文字
├─ website/       網站文案、資訊架構、SEO 與頁面規劃
├─ telegram/      Telegram 訊息、流程、活動與社群營運
├─ channels/      跨平台發布渠道規劃
├─ operations/    日常營運、SOP、檢查清單與排程
├─ outputs/       草稿、發布成品、報告與交付物
├─ legal/         授權、隱私、合約與使用權紀錄
├─ finance/       預算、定價、支出與商業資料
└─ archive/       舊版本、停用素材、備份與歷史紀錄
```

## 命名原則

- 資料夾使用英文小寫與連字號，例如 `quality-reviews`。
- 文件使用日期、主題、版本，例如 `2026-07-09_brand-voice_v01.md`。
- 草稿、正式版、封存版要分開保存。
- 不確定用途的資料先放入對應資料夾的草稿區，不要直接放在根目錄。
- 過期但有參考價值的內容移入 `archive/`。

## 重要文件

- [Image Factory V1](image_factory/README.md)
- [專案分析與結構調整](docs/PROJECT_AUDIT.md)
- [AI 圖片工廠需求規劃](docs/requirements/image-factory/README.md)
- [AI 圖片工廠實作路線圖](docs/requirements/image-factory/IMPLEMENTATION_ROADMAP.md)
- [AI 圖片工廠工作流](workflows/image-factory/README.md)
- [AI 影片工廠需求設計](docs/requirements/video-factory/README.md)
- [AI 影片工廠實作路線圖](docs/requirements/video-factory/IMPLEMENTATION_ROADMAP.md)
- [AI 影片工廠工作流](workflows/video-factory/README.md)
