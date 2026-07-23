# images/factory

AI 圖片工廠的圖片與圖片相關資料集中放在這裡。

## 子資料夾

- `generated/`：生成後的圖片
- `metadata/`：每張圖片對應的 metadata

## 日期分類規則

```text
images/factory/generated/YYYY/MM/DD/
images/factory/metadata/YYYY/MM/DD/
```

範例：

```text
images/factory/generated/2026/07/09/
images/factory/metadata/2026/07/09/
```

## 圖片命名規則

```text
YYYYMMDD_HHMMSS_image-factory_task-id_v01.png
```

範例：

```text
20260709_103000_image-factory_if-000001_v01.png
```

## 不建議

- 不要直接把圖片散放在 `images/` 根目錄
- 不要使用 `final.png`、`test.png`、`new.png` 這類難以追蹤的檔名
- 不要覆蓋舊圖片，改用新版本號

