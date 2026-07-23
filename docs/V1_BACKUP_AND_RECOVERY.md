# V1 Backup And Recovery

Product: Temple Product Video Generator

Version: 1.0.0

## Data Location

Development data:

```text
apps\temple-product-video-generator\data\
```

Production data:

```text
D:\AI\Temple Product Video Generator\data\
```

The data folder contains:

- product records
- uploaded product photos
- video projects
- scene data
- preview videos
- export packages
- backups
- evidence screenshots
- logs
- support packages

## Create Backup

From the Settings screen, click:

```text
建立資料備份
```

Production backups are saved in:

```text
D:\AI\Temple Product Video Generator\data\backups\
```

Backup folders and ZIP files are timestamped.

## Restore Backup

1. Open Settings.
2. Select the backup `.zip` file.
3. Type:

```text
RESTORE
```

4. Click:

```text
還原備份
```

Before restore, the application creates a safety backup of the current data. Restore never overwrites data without the `RESTORE` confirmation text.

## Recovery Validation

The production rehearsal verified that a restored project can:

- open successfully
- display scenes
- retain product photos
- retain settings
- export again

Validated production rehearsal backup:

```text
D:\AI\Temple Product Video Generator\data\backups\temple-product-video-generator-backup-20260724-013040.zip
```

## Safe Cleanup

Temporary frame and clip files can be cleaned after a successful backup if the final MP4 no longer needs regeneration.

Do not delete:

```text
D:\AI\Temple Product Video Generator\data\
```

This folder contains operational product, project, upload, export and recovery data.
