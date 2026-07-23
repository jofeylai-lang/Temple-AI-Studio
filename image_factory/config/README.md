# config

此資料夾存放 Image Factory V1 的設定規劃。

目前不放 API Key，不放帳號密碼，不放任何私密金鑰。

## 建議設定類型

- 預設 Provider
- 預設圖片尺寸
- 預設模型名稱
- 預設 negative prompt
- output 日期分類規則
- metadata 欄位規則
- logs 寫入規則

## 設定原則

- 機密資料未來應放在 `.env`，不可提交到 Git
- Provider 設定只描述欄位，不放真實金鑰
- 不同 Provider 的設定放在 `config/providers/`

