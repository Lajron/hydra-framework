# Agent Skill Adapter Surface

This directory exists for provider skill discovery.

Hydra source of truth lives in `.hydra-framework/`. Generated files under this directory should identify their canonical Hydra source and should be regenerated with:

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters
```

Do not store secrets, personal preferences, local MCP auth, or machine-specific paths here.
