# Provider Config

此資料夾規劃各圖片生成 Provider 的設定欄位。

每個 Provider 都應該能被切換或替換，而不影響 Prompt 管理、output 分類與 metadata 格式。

## Provider 共用設定欄位

```text
provider_name:
enabled:
default_model:
default_size:
default_seed:
supports_negative_prompt:
supports_seed:
supports_batch:
notes:
```

## 預計支援 Provider

- `openai_images`
- `flux`
- `stable_diffusion`
- `comfyui`
- `google_imagen`

