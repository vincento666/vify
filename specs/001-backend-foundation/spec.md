# Spec 001: Backend Foundation

## Goal

Create the FastAPI backend skeleton, shared infrastructure, database baseline,
and testing harness required by all later features.

## Slices

| Slice | User/Developer Value | Acceptance Gates |
|------|----------------------|------------------|
| 001.1 Python project skeleton | Developer can install and run backend with Python 3.12 | RED: project command test fails before files; Unit: config smoke; Integration: app imports; E2E: N/A; UAT: N/A |
| 001.2 FastAPI app and envelope | `GET /api/v1/health` returns `{code,message,data}` | RED: contract test fails; Unit: response model; Integration: TestClient route; E2E: N/A; UAT: browser hits health JSON |
| 001.3 Error handling | `BizError` maps to stable error envelope | RED: error route contract fails; Unit: error code model; Integration: exception handler; E2E: N/A; UAT: browser displays JSON |
| 001.4 SQLAlchemy/Alembic baseline | Target tables from spec 000 are owned by Alembic | RED: migration table assertion fails; Unit: ORM metadata; Integration: alembic upgrade on test DB; E2E: N/A; UAT: DB inspect note |
| 001.5 Redis/settings/logging/metrics | Shared runtime services are configured and observable | RED: readiness/metrics tests fail; Unit: settings; Integration: `/readyz` and `/metrics`; E2E: N/A; UAT: browser opens endpoints |

## Required Tests

- `tests/unit/core/test_responses.py`
- `tests/unit/core/test_errors.py`
- `tests/integration/test_health.py`
- `tests/integration/test_alembic_baseline.py`
- `tests/contract/test_error_envelope.py`

## Browser UAT

Open:

- `/api/v1/health`
- `/readyz`
- `/metrics`

Expected: health/readiness JSON is visible; metrics text is visible when enabled.
