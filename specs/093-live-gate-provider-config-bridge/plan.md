# Plan 093

## 093.1 Opt-In Model Config Resolver

- Add RED acceptance coverage using a temporary local provider/model config DB
  and a local OpenAI-compatible server.
- Add an opt-in resolver keyed by
  `HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID`.
- Preserve direct env credential precedence and artifact redaction.
- Fail closed for ambient DB fallback, unsupported provider types, and
  credential-bearing provider URLs.
- Record formal live gate status: either run through provider config if present
  or keep the goal blocked with explicit missing-env evidence.

## Gates

- RED acceptance failure before implementation.
- Green focused acceptance tests for local compatible provider and provider
  config bridge.
- Green security regression tests for direct-env precedence, no ambient DB
  fallback, unsupported provider type rejection, and credential URL rejection.
- Ruff for touched Python files.
- No browser UAT required; this is a backend acceptance harness capability.
