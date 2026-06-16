# Spec 093: Live Gate Provider Config Bridge

## Goal

Allow the formal customer-assistant live acceptance gate to resolve an
OpenAI-compatible provider/model from Hify's configured provider store, so the
gate can run in demo environments where the app already has provider credentials
without copying API keys into shell environment variables.

## Acceptance Criteria

- When the live gate flag is enabled and
  `HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID` points to an enabled model
  config, the gate resolves provider type, base URL, API key, and model id from
  the database.
- Direct `HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY` / `OPENROUTER_API_KEY`
  environment variables continue to take precedence.
- Evidence artifacts do not print provider API keys or DB credentials.
- Missing/disabled provider config fails closed with a clear reason; default CI
  remains skipped unless the live flag is enabled.
- Bridge mode requires an explicit `HIFY_DATABASE_URL` in the provided live gate
  environment, rejects unsupported provider types, and rejects provider URLs
  containing credentials.

## Non-goals

- Do not auto-discover arbitrary provider configs without an explicit model
  config id.
- Do not print or export provider secrets.
- Do not change provider CRUD APIs.
- Do not fall back to ambient process database credentials when the caller passes
  an explicit env mapping.

## Evidence

Evidence lives under
`artifacts/slices/093-live-gate-provider-config-bridge/093.1/`.
