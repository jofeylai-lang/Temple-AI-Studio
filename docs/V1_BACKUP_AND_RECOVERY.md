# V1 Backup And Recovery

## 資料位置

預設資料夾：

```text
apps/temple-product-video-generator/data/
```

包含：

- 商品資料
- 商品照片
- 影片專案
- 預覽影片
- 匯出內容包
- 備份
- 操作證據圖

## 建立備份

在應用程式「設定」頁按：

```text
建立資料備份
```

備份會建立在：

```text
apps/temple-product-video-generator/data/backups/
```

## 還原備份

1. 到「設定」頁。
2. 選擇備份 zip。
3. 在確認欄輸入 `RESTORE`。
4. 按「還原備份」。

系統會先建立一份安全備份，再執行還原。

## 手動備份

關閉應用程式後，複製整個資料夾：

```text
apps/temple-product-video-generator/data/
```

## 復原原則

- 不會在未確認情況下覆蓋資料。
- 刪除商品或專案紀錄不會自動刪除原始輸出檔。
- 若專案狀態不完整，可從「生成進度」重新組裝預覽或重新匯出。
