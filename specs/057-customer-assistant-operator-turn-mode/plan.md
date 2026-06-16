# Plan 057: Customer Assistant Operator Turn Mode

## Implementation Shape

Add a turn-mode classifier before task recognition:

```text
actor + message + session context -> turnMode
```

For MVP, this can be deterministic with optional LLM support behind the 055
runtime mode.

Add an operator advisory orchestrator:

```text
operator message
  + task ledger summary
  + event summary
  + knowledge snippets
  + Chatflow/SOP metadata
  + optional harness/sub-agent summaries
  -> operator recommendation
  -> optional proposed task command
```

This is a read-only orchestration path by default.

## Data Model

Persist turn mode in:

- run input payload;
- runtime event payloads;
- eval exported cases;
- frontend event timeline.

## Proposed Task Commands

Represent operator-suggested ledger mutations as proposed actions or a new
`proposed_task_command` structure. They must not mutate the ledger until
confirmed.

## Tests

Key tests:

- operator refund phrasing does not create task;
- customer refund phrasing creates task;
- operator asks advice and gets recommendation;
- missing knowledge/Chatflow context produces visible warning, not an empty
  recommendation shell;
- advisory path can include knowledge and Chatflow/SOP evidence summaries;
- operator confirms proposed command and ledger mutates;
- idempotency includes actor and mode.
