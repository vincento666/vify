# Plan: Customer Assistant Spawn Tenant Access

## Slice 116.1

Tighten the customer-assistant sub-agent harness path so it participates in the same tenant and audit model as the rest of the productized operator API.

## Approach

1. Add a failing integration test that creates a tenant A session and attempts to spawn a sub-agent from tenant B.
2. Add a failing integration test that verifies same-tenant background execution records host-context audit evidence.
3. Pass `RequestContext` into the foreground spawn service and into the background worker service.
4. Append a sanitized `session_context_snapshot` event during background sub-agent execution.
5. Run focused integration, nearby customer-assistant API regressions, and ruff.

## Test Strategy

- Focused integration test: `tests/integration/customer_assistant/test_spawn_sub_agent_tenant_access.py`.
- Nearby regression coverage: worker profile tenancy, operator audit, task controls, proposed-action lifecycle, and runtime e2e tests.
- Static gate: `ruff check` for touched Python files.

## Browser UAT

No new browser-visible control is added in this slice. The final customer-assistant browser story UAT remains covered by slice 115 and the final MVP gate bundle.

## Risks

- FastAPI background tasks run after the response; the test polls the run/event state rather than assuming immediate completion.
- Request context is immutable, so passing it into the background task is safe for this local execution model.
