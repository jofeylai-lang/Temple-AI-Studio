# prompts

Image Factory V1 的 Prompt 全部集中管理在此資料夾。

Provider 不應該直接保存 Prompt。Provider 只接收已整理好的 Prompt。

## 子資料夾

- `system/`：系統層級 Prompt 規則
- `styles/`：風格 Prompt
- `negative/`：負面 Prompt
- `templates/`：圖片生成 Prompt 模板

## Prompt 管理原則

- 原始一句話必須保留
- 最終 Prompt 必須保留
- negative prompt 必須保留
- Prompt 修改要新增版本，不覆蓋舊版本
- 每張圖片 metadata 要能追到 Prompt

