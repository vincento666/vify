# Plan 007: Workflow Replica

## Architecture

- Persist workflows through SQLAlchemy models.
- Implement `NodeExecutor` protocol and registry.
- Keep execution engine deterministic and bounded by `MAX_STEPS=50`.
- Use provider and knowledge facades instead of importing infra modules.

## Slice Order

007.1 -> 007.2 -> 007.3 -> 007.4 -> 007.5
