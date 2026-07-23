# GPT-SoVITS 語音系統

本目錄負責 Jofey AI Studio 的長期語音模型訓練與推理整合。

## 設計原則

- GPT-SoVITS 使用獨立 Python 環境，不共用 ComfyUI 的 `.venv`。
- 原始語音、處理後資料、模型權重及生成成品分開保存。
- 只有本人或已取得明確授權的聲音可以進入訓練流程。
- 訓練完成的 WAV 再交給 ComfyUI／LTX LipDub 或 Audio-to-Video。
- 大型權重與私人語音資料不提交 Git。

## 系統位置

```text
D:\AI\tools\GPT-SoVITS                    官方程式與獨立執行環境
D:\AI\Jofey AI Studio\datasets\raw\voice 原始錄音
D:\AI\Jofey AI Studio\datasets\licensed\voice 授權紀錄
D:\AI\Jofey AI Studio\datasets\processed\gpt-sovits 切割與標註資料
D:\AI\Jofey AI Studio\models\voice\gpt-sovits 訓練權重
D:\AI\Jofey AI Studio\outputs\voice\gpt-sovits 推理成品
```

## 執行階段

1. 建立說話者專案與授權紀錄。
2. 收集 15 至 30 分鐘乾淨語音作為第一版資料集。
3. 切成 3 至 10 秒 WAV 並校對逐字稿。
4. 執行 GPT-SoVITS 資料預處理。
5. 訓練 SoVITS 與 GPT 權重。
6. 使用未出現在訓練集的句子驗收。
7. 將合格語音輸出給 ComfyUI 影片工作流程。

## 第一版建議環境

```text
Python 3.10
CUDA 12.8 相容 PyTorch
NVIDIA RTX 5080 16GB
FFmpeg
```

正式安裝前應再次依官方最新版確認 PyTorch 與 Blackwell GPU 相容性。

