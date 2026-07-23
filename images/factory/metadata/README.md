# metadata 規格

每張生成圖片都應有一份對應 metadata。

## 建議檔名

```text
YYYYMMDD_HHMMSS_image-factory_task-id_v01.metadata.md
```

## 建議欄位

```text
# Image Metadata

task_id:
created_at:
source_input:
final_prompt:
negative_prompt:
model:
image_size:
aspect_ratio:
style:
seed:
output_file:
prompt_record:
status:
notes:
```

## 欄位說明

- `task_id`：生成任務 ID
- `created_at`：建立時間
- `source_input`：使用者原始一句話
- `final_prompt`：實際送去生成圖片的 Prompt
- `negative_prompt`：負面提示詞
- `model`：使用的圖片模型
- `image_size`：圖片尺寸
- `aspect_ratio`：圖片比例
- `style`：風格標籤
- `seed`：可重現用的種子值，如模型支援
- `output_file`：圖片檔路徑
- `prompt_record`：Prompt 紀錄路徑
- `status`：成功、失敗、重試中
- `notes`：補充說明

