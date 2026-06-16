# Spec 086: Host-Managed Persistence Mode

## Goal

Prevent production/host-style startup from mutating the database schema while
preserving the existing local/test bootstrap behavior.

## Acceptance Criteria

- Default local startup still calls `initialise_database()`.
- `persistence_mode=host` skips startup DDL.
- `persistence_mode=check` also skips startup DDL, reserving schema validation
  for an explicit check path.
- The setting is configurable through `HIFY_PERSISTENCE_MODE`.

## Non-goals

- Do not add Alembic migrations in this slice.
- Do not remove local `create_all` bootstrap.
- Do not connect to a real MySQL server without explicit credentials.

## Evidence

Evidence lives under
`artifacts/slices/086-host-managed-persistence-mode/086.1/`.
