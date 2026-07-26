# 228.2 TDD Preflight

- method: `tdd`
- date: 2026-07-26
- branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- worktree: `/Users/vincento/.codex/worktrees/560c/hify`
- implementation writes before this preflight: none
- live/paid provider budget: 0

## Capability recovery

- `rtk orbctl start`: PASS
- `rtk docker info`: PASS; OrbStack Docker server available
- `rtk docker compose -f docker-compose.mysql8-weaviate.yml up -d mysql8`:
  PASS
- `docker compose ... ps mysql8`: `healthy`
- `rtk uv run alembic upgrade head`: PASS through
  `0036_ai_assistant_tenant_scope`
- `rtk sh -lc 'PYTHONPATH=. uv run alembic heads'`: PASS; one head
  `0036_ai_assistant_tenant_scope`
- `rtk uv run alembic check`: BASELINE RED; existing metadata registration
  omits RuntimeLab/agent execution tables and exposes
  `ai_assistant_memory_cursor.pending_source_hash` drift. This is not reported
  as PASS and is not a Docker capability failure.

## Frozen RED

1. Golden and historical replay ignore the injected production route port and
   continue to call `_candidate_decision()`.
2. A candidate profile threshold change that changes the shared RuntimeLab
   route decision therefore remains false green.
3. The public RuntimeLab command path and governance replay lack a MySQL parity
   proof.

## Minimum GREEN boundary

- make `RuntimeLabService.handle_message()` delegate route selection to one
  side-effect-free preview method;
- make both governance replay modes require and call an injected route replay
  port;
- compose that port with the same RuntimeLab service builder used by the public
  command path;
- retain API envelope and persistence contracts;
- do not implement uncertainty, candidate fusion, authorization, or composite
  intent behavior in this slice.
