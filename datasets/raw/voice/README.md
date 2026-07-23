# 原始語音資料

每位說話者使用獨立資料夾：

```text
voice/
└── speaker_001/
    ├── session_01.wav
    └── session_02.wav
```

建議使用單人、無音樂、無回音的 WAV。不要在此處修改原始檔；所有切割、降噪與轉碼結果放入 `datasets/processed/gpt-sovits`。

