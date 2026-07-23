# ComfyUI Provider

未來支援 ComfyUI 工作流。

## V1 狀態

只做架構規劃，不連接 ComfyUI。

## 未來設定欄位

```text
provider: comfyui
workflow_file:
server_url:
checkpoint:
seed:
size:
output_node:
```

## 注意事項

- ComfyUI workflow 應獨立保存
- metadata 應記錄 workflow 檔案版本
- 不在 V1 放入真實 server URL 或 API 設定

