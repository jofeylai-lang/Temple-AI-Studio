# V1 Production Deployment Report

Product: Temple Product Video Generator

Version: 1.0.0

Date: 2026-07-24

Status: PASS

## Version Freeze

Accepted commit:

```text
f4696d7 chore: finalize product video generator v1 acceptance
```

Annotated tag:

```text
v1.0.0
```

Tag target:

```text
f4696d7723b99199c9c988017f2d09190ee62d90
```

Tag message:

```text
Temple Product Video Generator V1 production release
```

## Production Installation

Production root:

```text
D:\AI\Temple Product Video Generator
```

Application folder:

```text
D:\AI\Temple Product Video Generator\app
```

Data folder:

```text
D:\AI\Temple Product Video Generator\data
```

No existing production user data was overwritten.

During deployment validation, an incorrect first extraction was detected and backed up before redeploying the correct app folder:

```text
D:\AI\Temple Product Video Generator\deployment-backups\
```

## Launcher

```text
D:\AI\Temple Product Video Generator\start.bat
```

The launcher opens the browser automatically and avoids starting a duplicate server if port `4173` is already listening.

Desktop shortcut:

```text
C:\Users\User\Desktop\Temple 商品影片產生器 V1.lnk
```

## Release Package

```text
D:\AI\Jofey AI Studio\apps\temple-product-video-generator\release\TempleProductVideoGenerator-1.0.0.zip
```

## Operational Hardening Added After Acceptance

- production data separation
- duplicate-process launcher behavior
- Traditional Chinese operator text repair
- support package generation
- application logs
- generation logs
- FFmpeg error logs
- recovery logs
- production operator handoff
- upgrade and rollback instructions
- safe schema migration guard
- sanitized support package
- repeatable deployment script

## Production Rehearsal

Project:

```text
project-20260724-11969a6e
```

Final MP4:

```text
D:\AI\Temple Product Video Generator\data\exports\project-20260724-11969a6e\final_video.mp4
```

Backup:

```text
D:\AI\Temple Product Video Generator\data\backups\temple-product-video-generator-backup-20260724-013040.zip
```

Support package:

```text
D:\AI\Temple Product Video Generator\data\support\temple-product-video-generator-support-20260724-014949.zip
```

Evidence:

```text
D:\AI\Temple Product Video Generator\data\evidence\20260724-013041\
```

Validated:

- production one-click launch
- clean first run
- product create
- multiple image upload
- image sort
- image replace
- generation
- scene edit
- scene approval
- exactly one scene regeneration
- approved scene content preserved
- MP4 export
- restart persistence
- backup
- restore
- re-export after restore
- support package privacy
- Traditional Chinese operator text
- application-side evidence PNG generation
- desktop shortcut creation
- Windows path with spaces

## Defects Found And Fixed

- Initial production extraction placed the wrong folder shape in `app`; the faulty app folder was backed up and redeployed.
- Deployment script initially assumed a wrapped ZIP root; it now supports the accepted release ZIP structure.
- Deployment script originally had no help guard; it now supports `-Help`.
- Production launcher generation now writes ASCII batch files to avoid Windows UTF-8 BOM launch issues.
- Operator-facing Traditional Chinese text in the UI, README, handoff guide and quick-start guide was repaired.
- Final validation script initially treated an `/api/files/...` URL as a Windows path; the recorded validation now points to the real MP4 file.

## Final Result

PASS.
