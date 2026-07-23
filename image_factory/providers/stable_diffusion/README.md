# Stable Diffusion Provider

未來支援 Stable Diffusion。

## V1 狀態

只做架構規劃，不執行生成。

## 未來設定欄位

```text
provider: stable_diffusion
checkpoint:
vae:
sampler:
steps:
cfg_scale:
seed:
size:
```

## 注意事項

- checkpoint 與 LoRA 版本必須記錄
- negative prompt 通常很重要
- 建議完整保存 seed 與參數

