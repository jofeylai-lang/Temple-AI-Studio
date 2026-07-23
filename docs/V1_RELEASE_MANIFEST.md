# V1 Release Manifest

Product: Temple Product Video Generator

Release Version: 1.0.0

Date: 2026-07-24

## Release Package

```text
D:\AI\Jofey AI Studio\apps\temple-product-video-generator\release\TempleProductVideoGenerator-1.0.0.zip
```

Release folder:

```text
D:\AI\Jofey AI Studio\apps\temple-product-video-generator\release\TempleProductVideoGenerator-1.0.0\
```

## Package Contents

- `start.bat`
- `server.py`
- `index.html`
- `styles.css`
- `package.json`
- `config.sample.json`
- `README.md`
- `README_ZH_TW.txt`
- `VERSION.txt`
- `src/app.js`
- `sample-data/sample-product-photo.png`
- `sample-data/sample-product-project.json`
- `docs/V1_BACKUP_AND_RECOVERY.md`
- `docs/V1_CEO_ACCEPTANCE_REPORT.md`
- `docs/V1_FINAL_QA_REPORT.md`
- `docs/V1_IMPLEMENTATION_REPORT.md`
- `docs/V1_KNOWN_LIMITATIONS.md`
- `docs/V1_RELEASE_MANIFEST.md`
- `docs/V1_RELEASE_NOTES.md`
- `docs/V1_USER_QUICKSTART_ZH_TW.md`
- `docs/V1_VALIDATION_REPORT.md`

## Data Policy

The package does not include user `data/`.

When launched, the app creates:

```text
data/
data/uploads/
data/projects/
data/exports/
data/backups/
data/evidence/
```

## Backup

Use Settings -> 建立資料備份.

Backup files are created at:

```text
data/backups/
```

## Restore

Use Settings -> 還原備份.

Restore requires typing:

```text
RESTORE
```

## Uninstall

To remove the application, delete the application folder.

Warning:

Do not delete `data/` unless product photos, projects, exports, and backups are no longer needed.

## Git Exclusions

Ignored:

- `apps/temple-product-video-generator/data/`
- `apps/temple-product-video-generator/runtime/`
- `apps/temple-product-video-generator/release/`
- `apps/temple-product-video-generator/__pycache__/`

This prevents private media, generated videos, backups, runtime files, and release binaries from being committed.
