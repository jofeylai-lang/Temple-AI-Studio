# V1 Upgrade And Rollback

Product: Temple Product Video Generator

Version: 1.0.0

## Upgrade Policy

V1 uses local application files and a separate production data folder.

Application:

```text
D:\AI\Temple Product Video Generator\app
```

Data:

```text
D:\AI\Temple Product Video Generator\data
```

## Before Upgrade

1. Stop the app.
2. Back up data from Settings, or copy:

```text
D:\AI\Temple Product Video Generator\data
```

3. Back up the app folder:

```text
D:\AI\Temple Product Video Generator\app
```

## Data Version

The local database includes:

```text
schemaVersion: 1
```

The app version is:

```text
1.0.0
```

## Migration Rule

No silent destructive migration is allowed.

Future migrations must:

- create a pre-upgrade backup
- keep user data
- document schema changes
- provide rollback notes

Current startup behavior:

- If a database has no schema version or an older schema version, the app writes a migration backup before updating metadata.
- If a database is newer than the app supports, startup returns a clear error instead of silently modifying data.

## Rollback

1. Stop the app.
2. Restore the backed-up `app` folder.
3. Restore data from backup if needed.
4. Launch:

```text
D:\AI\Temple Product Video Generator\start.bat
```
