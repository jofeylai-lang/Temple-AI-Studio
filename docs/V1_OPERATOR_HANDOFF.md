# V1 Operator Handoff

Product: Temple Product Video Generator

Version: 1.0.0

## How To Start

Double-click:

```text
D:\AI\Temple Product Video Generator\start.bat
```

The launcher opens the browser automatically.

If the service is already running, the launcher opens the browser and does not start a second copy.

Desktop shortcut:

```text
C:\Users\User\Desktop\Temple 商品影片產生器 V1.lnk
```

## Daily Workflow

1. Open `商品資料庫`.
2. Create or select a product.
3. Upload product photos.
4. Sort, replace or remove photos if needed.
5. Open `建立影片`.
6. Enter the Traditional Chinese video request.
7. Generate the content package and preview video.
8. Open `影片預覽`.
9. Inspect caption, SEO keywords, thumbnail suggestion and scene list.
10. Open `場景細節` if one scene needs editing.
11. Save, approve or regenerate exactly one scene.
12. Approve the complete video.
13. Open `輸出`.
14. Export the complete package.

## Where Files Are Saved

Exports:

```text
D:\AI\Temple Product Video Generator\data\exports
```

Product photos:

```text
D:\AI\Temple Product Video Generator\data\uploads
```

Backups:

```text
D:\AI\Temple Product Video Generator\data\backups
```

Support packages:

```text
D:\AI\Temple Product Video Generator\data\support
```

## How To Back Up

Open `設定` and click:

```text
建立資料備份
```

## How To Restore

Open `設定`, select the backup zip, type:

```text
RESTORE
```

Then click:

```text
還原備份
```

The app creates a safety backup before restore.

## How To Stop

Close the launcher window that says:

```text
Temple Product Video Generator V1
```

If a browser tab remains open, close the tab.

## If Generation Fails

Open `生成進度`.

Use:

- `重新產生影片`
- `場景細節` then `只重產此場景`
- `建立支援包` from Settings if the issue needs review

## How To Create A Support Package

Open `設定` and click:

```text
建立支援包
```

Support packages are saved in:

```text
D:\AI\Temple Product Video Generator\data\support
```

The support package excludes product photos, generated videos, database content, prompts, captions, narration, API keys, tokens, passwords and customer-sensitive output.
