# Plan 086

## 086.1 Startup DDL Mode Gate

- Add a RED unit test that exercises FastAPI lifespan with host/check settings
  and proves startup DDL is still attempted.
- Add `persistence_mode` to settings and gate startup initialization in
  `app/main.py`.
- Keep local/test modes initializing the database.

## Gates

- RED unit failure before implementation.
- Green focused unit test.
- Ruff for touched app/test files.
- Browser UAT is not applicable because this slice changes backend startup
  behavior only.
