# Capability Benchmarks

Purpose:

Store benchmark work packages and benchmark evidence for every major Temple AI Studio capability.

Source registry:

```text
evaluations/capability-registry.json
```

Generated work packages:

```text
evaluations/capabilities/<capability-id>/BENCHMARK_WORK_PACKAGE.md
```

Regenerate with:

```powershell
python scripts\temple_ai_studio\generate_capability_benchmarks.py
```

Validate registry with:

```powershell
python scripts\temple_ai_studio\validate_capability_registry.py
```

Do not commit private CEO source material, generated videos, voices, product photos, tokens or paid provider credentials.
