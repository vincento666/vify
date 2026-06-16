# Tasks 057: Customer Assistant Operator Turn Mode

## 057.0 Sign-off

- [x] Confirm operator turns are recommendation-only by default.
- [x] Confirm customer task turns keep existing behavior.
- [x] Confirm `operator_recommendation_turn` does not enter the customer task
      state machine or dispatch task workers by default.
- [x] Confirm operator advisory can use knowledge, Chatflow/SOP metadata, and
      harness/sub-agent summaries without mutating the ledger.
- [x] Confirm task ledger mutation from operator requires explicit confirmation.

## 057.1 Turn Mode Classifier

- [x] RED: operator-turn test fails because operator input mutates ledger.
- [x] Add turn mode classifier.
- [x] Route `operator_recommendation_turn` away from the task-recognition
      mutation path.
- [x] Persist turn mode in run/event payloads.

## 057.2 Operator Advisory Context Pack

- [x] RED: operator advice test fails because recommendation is an empty shell.
- [x] Build context pack from task ledger and events.
- [x] Add optional knowledge-base snippets.
- [x] Add optional Chatflow/SOP metadata summary from database-backed bindings.
- [x] Add warnings for missing context sources.

## 057.3 Recommendation-only Operator Path

- [x] Add recommendation-only path that uses the advisory context pack.
- [x] Ensure no `ADD_TASK`, `RETAIN_TASK`, `SUSPEND_TASK`, `RESUME_TASK`,
      `CANCEL_TASK`, `CALL_WORKER`, or worker dispatch occurs by default.
- [x] Emit operator-turn events.

## 057.4 Harness Advisory Worker

- [x] Add bounded read-only harness/sub-agent call shape for advisory work.
- [x] Stream or persist advisory worker events where available.
- [x] Ensure advisory workers cannot mutate the ledger directly.

## 057.5 Proposed Task Command

- [x] RED: proposed command confirmation test fails.
- [x] Add proposed task command representation.
- [x] Add confirmation path that applies ledger mutation.

## 057.6 Frontend

- [x] Distinguish operator question from customer request in the panel.
- [x] Show proposed task command confirmation where applicable.
- [x] Show advisory evidence/warnings when knowledge or Chatflow context is
      missing.
- [x] Run focused tests, rem gate, and build.

## 057.7 Browser UAT

- [x] Verify customer refund creates task.
- [x] Verify operator refund phrasing does not create task.
- [x] Verify operator advice appears in the operator lane with evidence or
      missing-context warnings.
- [x] Verify confirmed proposed command mutates the ledger.
