# Tasks 001: Backend Foundation

## 001.1 Python project skeleton

- [x] RED: command/import test fails before skeleton exists.
- [x] Create `pyproject.toml` with Python 3.12 constraints.
- [x] Create package layout.
- [x] Unit gate passes.
- [x] Integration import gate passes.
- [x] E2E marked N/A for non-browser skeleton.
- [x] Browser UAT marked N/A with import evidence.

## 001.2 FastAPI app and envelope

- [x] RED: `/api/v1/health` contract test fails.
- [x] Implement health route.
- [x] Unit gate passes.
- [x] Integration gate passes.
- [x] E2E gate passes against `uvicorn`.
- [x] Browser UAT captures health response.

## 001.3 Error handling

- [x] RED: `BizError` contract test fails.
- [x] Implement error code and exception handler.
- [x] Unit and contract gates pass.
- [x] E2E gate passes against `uvicorn`.
- [x] Browser UAT captures error envelope.

## 001.4 SQLAlchemy/Alembic baseline

- [x] RED: target table assertion fails.
- [x] Implement ORM base and first migration.
- [x] Alembic upgrade test passes.
- [x] E2E Alembic CLI upgrade passes with `HIFY_DATABASE_URL`.
- [x] Record schema evidence.
- [x] Browser UAT captures schema report.

## 001.5 Runtime services

- [x] RED: readiness/metrics tests fail.
- [x] Implement settings, logging, Redis health, metrics endpoint.
- [x] Unit gate passes.
- [x] Integration gate passes.
- [x] E2E gate passes against `uvicorn`.
- [x] Browser UAT captures `/readyz` and `/metrics`.
