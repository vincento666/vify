# Plan 001: Backend Foundation

## Architecture

- `app/main.py`: FastAPI app factory and router registration.
- `app/core/config.py`: Pydantic Settings.
- `app/core/responses.py`: `Result` and `PageResult`.
- `app/core/errors.py`: `ErrorCode` and `BizError`.
- `app/core/database.py`: SQLAlchemy engine/session.
- `alembic/`: target schema baseline.
- `tests/`: pytest, httpx TestClient, Alembic test helpers.

## Notes

- Use Python 3.12 only.
- Use SQLAlchemy 2.0 style `select()`.
- Do not introduce business modules before foundation gates pass.
- Alembic baseline must include the schema superset from `000`.

## Slice Order

001.1 -> 001.2 -> 001.3 -> 001.4 -> 001.5
