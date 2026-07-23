# Metadata Schema

每張圖片都應建立同名 metadata 檔案。

## 必要欄位

```text
prompt:
negative_prompt:
model:
seed:
size:
created_at:
provider:
```

## 建議完整欄位

```text
task_id:
prompt:
negative_prompt:
model:
seed:
size:
width:
height:
created_at:
provider:
source_input:
prompt_template:
output_file:
status:
notes:
```

## 日期格式

建議使用：

```text
YYYY-MM-DDTHH:mm:ssZ
```

範例：

```text
2026-07-09T10:30:00+08:00
```

