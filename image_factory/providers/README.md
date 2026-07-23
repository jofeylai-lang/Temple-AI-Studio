# providers

此資料夾存放 Image Factory V1 的 Provider 模組設計。

目前只建立架構與說明，不加入真正呼叫 API 的程式。

## Provider 替換原則

每個 Provider 都應符合相同輸入與輸出概念：

### Input

```text
prompt
negative_prompt
model
size
seed
output_path
metadata_path
```

### Output

```text
status
image_file
metadata_file
provider
model
created_at
error_message
```

## 設計目標

- Provider 可以替換
- Prompt 不寫死在 Provider 裡
- output 路徑由 Image Factory 統一管理
- metadata 格式由 Image Factory 統一管理
- logs 由 Image Factory 統一管理

