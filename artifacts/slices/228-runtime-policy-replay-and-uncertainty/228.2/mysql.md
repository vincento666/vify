# MySQL capability evidence

- User authorized starting Hify Docker services and continuing.
- `rtk orbctl start`: PASS
- `rtk docker info`: PASS
- `rtk docker compose -f docker-compose.mysql8-weaviate.yml up -d mysql8`:
  PASS
- service status: `hify-mysql8` healthy
- `rtk uv run alembic upgrade head`: PASS through
  `0036_ai_assistant_tenant_scope`
- `rtk sh -lc 'PYTHONPATH=. uv run alembic heads'`: PASS; one head
  `0036_ai_assistant_tenant_scope`
- MySQL integration gate: PASS, 39 tests plus 3 subtests

`rtk uv run alembic check` remains a baseline RED and is not claimed as PASS:
current metadata registration omits existing RuntimeLab/agent execution tables
and exposes an existing memory cursor column drift. The database connectivity,
migration, and slice integration capabilities are independently proven above.
