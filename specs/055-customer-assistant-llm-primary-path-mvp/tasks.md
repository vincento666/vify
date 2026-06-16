# Tasks 055: Customer Assistant LLM Primary Path MVP

## 055.0 Sign-off

- [x] Confirm 054 readiness report allows starting 055.
- [x] Confirm Chatflow/SOP data readiness is green or explicitly mocked.
- [x] Confirm LLM primary is opt-in and deterministic remains default.
- [x] Confirm shadow mode only records candidate/diff evidence and cannot select
      LLM output.
- [x] Confirm proposed actions remain the only path for high-risk writes.

## 055.1 Runtime Mode Settings

- [x] RED: settings test fails because LLM primary mode does not exist.
- [x] Add runtime mode settings and config parsing.
- [x] Validate invalid modes fall back to deterministic.
- [x] Validate `shadow` mode keeps deterministic response/ledger/dispatch
      behavior unchanged.

## 055.2 Task Recognition Primary

- [x] RED: service test fails because valid LLM candidate is ignored in primary
      mode.
- [x] Add candidate selection policy.
- [x] Add fallback events for parse/schema/confidence/safety failures.
- [x] Add fallback event for missing database-backed Chatflow/SOP binding.
- [x] Ensure shadow task-recognition candidates cannot mutate ledger state or
      dispatch workers.
- [x] Prove deterministic fallback does not break existing 045 behavior.

## 055.3 Recommendation Primary

- [x] RED: recommendation test fails because LLM primary recommendation is not
      selected.
- [x] Select LLM recommendation only after schema and safety validation.
- [x] Persist selected-source events.
- [x] Ensure shadow recommendation candidates are stored as evidence only.

## 055.4 Safety And Proposed Actions

- [x] RED: high-risk direct-write candidate test fails.
- [x] Ensure high-risk writes become proposed actions.
- [x] Ensure execution still requires `CONFIRMED`.

## 055.5 Gates And UAT

- [x] Run backend unit/integration/contract/e2e gates.
- [x] Run frontend focused tests and build.
- [x] Run Browser UAT in fake primary mode.
- [x] Optionally run live provider UAT and save skipped evidence if unavailable.
