# V1 Support And Diagnostics

Product: Temple Product Video Generator

Version: 1.0.0

## Logs

Production logs are stored in:

```text
D:\AI\Temple Product Video Generator\data\logs
```

Log files:

- `app.log`
- `generation.log`
- `ffmpeg-error.log`
- `recovery.log`

## Support Package

Create from Settings:

```text
建立支援包
```

Support ZIP location:

```text
D:\AI\Temple Product Video Generator\data\support
```

Validated production support package:

```text
D:\AI\Temple Product Video Generator\data\support\temple-product-video-generator-support-20260724-014949.zip
```

## Support Package Includes

- application version
- schema version
- production data path
- tool connection status
- local configuration summary with sensitive fields redacted
- logs

## Support Package Excludes

- API keys
- tokens
- passwords
- product photos
- generated videos
- database content
- prompt text
- captions
- narration
- customer-sensitive exports

## FFmpeg Errors

If FFmpeg fails, details are written to:

```text
D:\AI\Temple Product Video Generator\data\logs\ffmpeg-error.log
```

## Recovery Logs

Backup, restore and render failures are written to:

```text
D:\AI\Temple Product Video Generator\data\logs\recovery.log
```

## Support Privacy Validation

The production support ZIP was inspected and contained only:

- `support-summary.json`
- `logs\app.log`
- `logs\generation.log`
- `logs\recovery.log`

No product photos, generated videos, local database, prompt records, captions, narration files, API keys, tokens or passwords were included.
