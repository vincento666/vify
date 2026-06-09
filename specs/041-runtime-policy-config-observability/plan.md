# Plan 041: Runtime Policy Config And Observability

## Architecture

```text
Host system / Swagger
  -> RuntimePolicyProfile API
  -> RuntimePolicyProfileService
  -> RuntimePolicyResolver
  -> RuntimeLabService
  -> RuntimeDecisionLogger
```

Runtime-lab should receive an effective policy object, not read raw env values
directly for operational parameters.

```text
request context
  -> tenant/bot/channel/session binding
  -> active RuntimePolicyProfile
  -> effective policy snapshot
  -> route execution
  -> decision log
```

## Data Model

Create isolated runtime policy tables:

```text
runtime_policy_profile
runtime_decision_log
```

Use JSON columns for nested profile sections at first, with typed request/DTO
validation at the API boundary. This keeps the demo module isolated while still
giving the host system full backend configurability.

## TDD Strategy

RED tests first:

- profile CRUD API fails before persistence exists;
- invalid thresholds are accepted before validation exists;
- runtime-lab still uses env-only classifier config before profile resolver is
  wired;
- fallback Agent remains hardcoded before profile-driven factory exists;
- decision log lacks policy snapshot before logger is wired;
- decision-log query filters do not exist.

GREEN:

- add profile repository/service/API;
- add profile schema validation;
- add resolver with env bootstrap fallback;
- add runtime factories for classifier and fallback Agent from profile;
- add decision logger and query API;
- keep frontend untouched.

## SDD Gate

041 may start only after 040 route evidence is available. It must not change
Chatflow, Knowledge, Provider, or Agent module ownership except through existing
facade/adapter calls.

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and evidence under:

```text
artifacts/slices/041-runtime-policy-config-observability/
  041.1/
  041.2/
  041.3/
  041.4/
```

041 is complete only when profile API, effective profile resolution, and
decision logging all pass backend gates with no frontend changes.

## Slice Progress

- 041.1 complete: profile table/repository/service/API and nested config
  validation passed RED, unit, contract, backend E2E, and browser UAT gates.
- 041.2 complete: effective policy resolution by binding, env fallback, and
  runtime-lab config sourcing from profile passed RED, unit, contract, backend
  E2E, and browser UAT gates.
- 041.3 complete: profile-driven LLM classifier construction, fallback Agent
  selection, disabled unsupported live fallback adapters, and runtime-lab
  service wiring passed RED, unit, contract, backend E2E, and browser UAT gates.
- 041.4 complete: runtime decision logs persist effective policy snapshots,
  route evidence, confidence signals, and query filters, while the default 040
  route matrix remains compatible across focused backend E2E gates and browser
  UAT.

## Non-Goals

- no frontend configuration UI;
- no profile activation release gate;
- no rollback workflow;
- no automatic threshold tuning;
- no mandatory live LLM credentials.
