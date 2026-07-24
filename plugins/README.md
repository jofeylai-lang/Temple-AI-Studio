# Temple Plugin SDK

Temple AI Studio plugins live under:

```text
plugins/<plugin-id>/plugin.json
```

Every plugin manifest must include:

- `id`
- `name`
- `version`
- `capabilities`
- `entryPoint`

The Temple OS Plugin Manager scans this folder locally and validates manifests.

Network installation, paid connectors and external activation require CEO approval.
