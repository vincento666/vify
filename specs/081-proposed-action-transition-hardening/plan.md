# Plan 081

## 081.1 Conditional Repository Transition

- Add RED repository integration test for expected-status transitions.
- Add `transition_proposed_action_status` with stale-row no-op behavior.
- Keep existing unconditional update helper for seed/test setup compatibility.
- Run focused repository tests and commit.

## 081.2 Execute Claim Uses Atomic Transition

- Add RED service/API test proving duplicate/stale execute cannot invoke the
  executor twice.
- Use the conditional transition for `CONFIRMED -> EXECUTING`.
- Preserve failed executor audit/error evidence.
- Run focused contract/integration gates and commit.

## Gates

- RED before each implementation slice.
- Focused repository/service/API tests.
- Existing customer-assistant action lifecycle regressions.
- Docs and artifacts updated per slice.
