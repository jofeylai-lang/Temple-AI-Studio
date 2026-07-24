# Emma Identity Core Usage

Emma Identity Core is the local identity gate for Temple AI Studio.

It initializes Emma's permanent identity rules, imports CEO-approved reference images, builds a reproducible visual fingerprint, and evaluates generated candidate images before they are used in production workflows.

## Commands

Run from the project root:

```powershell
python scripts/temple_ai_studio/emma_identity_core.py init
python scripts/temple_ai_studio/emma_identity_core.py status
python scripts/temple_ai_studio/emma_identity_core.py build-fingerprint
```

Import an approved Emma reference image:

```powershell
python scripts/temple_ai_studio/emma_identity_core.py import-reference --source "D:\path\to\approved-emma-reference.jpg" --kind face --label "front-face" --approved-by CEO
```

Evaluate a generated candidate image:

```powershell
python scripts/temple_ai_studio/emma_identity_core.py evaluate-image --candidate "D:\path\to\candidate.jpg"
```

Run the local self-test:

```powershell
python scripts/temple_ai_studio/emma_identity_core.py self-test --output evaluations/quality-reviews/emma-identity/emma-identity-core-self-test.json
```

## Storage

- Identity profile: `avatar/identity/emma.identity.json`
- Identity fingerprint: `avatar/identity/emma.fingerprint.json`
- Private reference media: `avatar/references/emma/`
- Quality reports: `evaluations/quality-reviews/emma-identity/`

## Safety

Reference photos are private source material and must not be committed to Git.

The current global `.gitignore` already excludes common image formats, including JPG and PNG files.

## Current Status

Emma Identity Core can run now, but production identity validation remains blocked until CEO-approved Emma reference images are imported.
