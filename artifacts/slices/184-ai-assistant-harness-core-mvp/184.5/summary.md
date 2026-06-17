# 184.5 Final Aggregate Acceptance

## Subagent Result Synthesis

### Dalton: Phase 0 Harness Kernel

- Modification scope: session/run/message/event/tool-call persistence,
  read-only Tool Registry, prompt assembler, event replay, and Phase 0 API.
- RED evidence: `184.1/red.txt`, `184.1/red-prompt.txt`.
- Implementation summary: deterministic `echo_context` harness loop persisted
  visible events and final result without business writes.
- Gates run: unit, integration, contract, E2E, lint, mypy, MySQL8 boundary.
- Remaining risk: real LLM/model calls intentionally deferred.

### Aquinas: Phase 1 Safety Boundary

- Modification scope: approval modes, permission decisions, sandbox policy,
  approval records, proposed actions, and approve/deny endpoints.
- RED evidence: `184.2/red.txt`.
- Implementation summary: high-risk business writes pause for approval and
  create proposed actions; unsafe shell-like calls are denied.
- Gates run: unit, integration, contract, E2E, lint, mypy, MySQL8 boundary.
- Remaining risk: scheduler-level read/write serialization deferred to a later
  spec.

### Mill: Phase 2/3 Product Shell

- Modification scope: frontend API client, center event echo, left session/run
  list, right run/task inspector, approval controls, and browser E2E script.
- RED evidence: `184.3/red.txt`, `184.4/red-backend.txt`,
  `184.4/red-frontend.txt`.
- Implementation summary: Hify light-style product shell renders persisted
  event cards and inspector state without exposing hidden reasoning.
- Gates run: frontend focused/unit, remScaleClosure, backend contract
  regression, browser UAT/E2E.
- Remaining risk: token/cost accounting remains placeholder-only.

## Aggregate Gate Matrix

- RED evidence index: `red-evidence-index.txt`.
- Backend unit: `backend-unit.txt` passed, 6 tests.
- Backend integration: `backend-integration.txt` passed, 2 tests.
- Backend contract: `backend-contract.txt` passed, 7 tests.
- Backend E2E: `backend-e2e.txt` passed, 2 tests.
- Frontend unit: `frontend-unit.txt` passed, 95 files / 371 tests.
- Frontend remScaleClosure: `remScaleClosure.txt` passed.
- Browser UAT / product-shell E2E: `browser-uat.txt` passed.

## Browser UAT

Target: `http://127.0.0.1:5173/ai-assistant`

Verified:

- left session and run list;
- center persisted event echo cards;
- right run/task inspector with tool call, approval, timeline, usage;
- high-risk update pauses at approval;
- Hify light content-area color style, not dark product-shell styling;
- no horizontal overflow at 1440 x 900.

Screenshot:

- `screenshots/ai-assistant-shell-final-uat.png`

## Residual Risks

- Phase 3 task panel derives task rows from run/event state. Durable task
  ledger and scheduler/RWMutex are deferred to spec 185.
- Token accounting fields are placeholders. Real token/cost/latency accounting
  is deferred to spec 188.
- Real LLM execution remains out of scope for spec 184 gates; future real-LLM
  tests should use OpenRouter via environment variables rather than committed
  credentials.
