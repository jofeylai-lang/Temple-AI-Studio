# GPT-SoVITS 處理後資料

建議結構：

```text
gpt-sovits/
└── speaker_001/
    └── v1/
        ├── wavs/
        │   ├── 0001.wav
        │   └── 0002.wav
        ├── train.list
        ├── validation.list
        └── dataset-report.md
```

標註格式：

```text
絕對音檔路徑|說話者名稱|ZH|完全對應的逐字稿
```

所有自動語音辨識結果都必須人工校對後才可訓練。

