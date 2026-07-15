# Loop State

- date: 2026-07-13
- mode: Open -> Closed Loop
- active spec: 225-runtime-lab-sop-live-stream
- active slice: 225.8 Cross-process Redis/outbox Stream-order Recovery
- phase: SLICE_CLOSED
- branch: codex/sop-runtime-v2-live-stream
- base: 828782ce
- worktree: /Users/vincento/work/develop/hify-sop-runtime-v2-live-stream

Current tracer: RuntimeLab `messages:stream` -> durable SOP child run -> Runtime
V2 event cursor -> compatible SSE envelope -> Vue incremental transcript.

225.6.1/225.6.2: RED -> GREEN. `ProviderBackedOpenAIChatClient` has an async
stream capability with timeout, cancellation propagation, retry-before-visible-
output only, and a process-local provider concurrency bound. Runtime V2 workers consume
that capability via their worker-owned event loop; synchronous callers retain
their facade. CA covers SSE, worker, async delta ordering, non-stream fallback,
partial failure, real Chatflow outer SSE, cancellation, and Shadow sync
compatibility. A reviewer identified a missing single-path proof that durable
Runtime V2 cancellation closes the real `ProviderBackedOpenAIChatClient` HTTP
stream; that end-to-end test is now GREEN. Next: independent re-review and
all-slice closeout gates. RuntimeLab/Chatflow broad regression passed (265
tests + 144 subtests before cancellation follow-up); current
transport/provider/CA focused rerun passed (46 before the new seam). Mypy
remains baseline-blocked (232 transitive
diagnostics; no new 225.6 diagnostic found).
Authorized live-provider UAT: PASS. OpenRouter `qwen/qwen3.5-27b` returned
two actual provider chunks, both durable before LLM-node completion and both
projected by RuntimeLab SSE as `source: provider`; the child run SUCCEEDED.
The three bounded attempts have a conservative combined cap below $0.0021 of
the user-authorized $0.10. Provider-side cancellation billing remains dependent
on the upstream host selected by OpenRouter.

225.7 contract confirmed: parallel LLM/KNOWLEDGE/safe TOOL waves, node timeout
fail-fast, structured failures, and upper-layer degradation. User explicitly
excluded a node-attempt ledger/migration, node-retry expansion, new queue, and
worker-capacity/deployment change. Current Runtime V2 already has explicit
frontier waves and API_CALL-only true parallel execution. A safe Tool must
receive a stable idempotency key before dispatch and provide a receipt;
nonconforming Tools are not parallel-safe. A terminal node failure or timeout
must preserve the failed workflow result and produce direct workflow
code/message/data plus RuntimeLab's compatible string `error` and additive
sanitized `failure`; Chatflow failure is turn-scoped and cannot poison the next
eligible user turn. Next: add 225.7 to tasks/spec/plan/verifiers and capture a
public LLM-fan-out overlap RED proof before minimal implementation.

225.7.1 LLM parallel wave: RED -> GREEN. The public Workflow fan-out test used
two deterministic async providers that fail unless both calls overlap. Before
the change, Runtime V2 prestarted both LLM runs but executed them serially and
the first failed with `second independent LLM did not start before the first
completed`. LLM is now in the existing frontier parallel whitelist. The test
also exposed shared SQLAlchemy connection misuse: parallel status probes and
live-delta persistence now create short-lived sessions from the engine, and
the LLM completer is resolved before worker threads start. Focused LLM/V2
regression: 17 passed; ruff and diff-check: PASS. Next: KNOWLEDGE overlap RED.

225.7.2 KNOWLEDGE parallel wave: RED -> GREEN. The Runtime V2 service-surface
test showed the same serial failure before allowing KNOWLEDGE in the existing
parallel frontier whitelist. Database-backed knowledge facades are reconstructed
with a worker-private short-lived session, while test/non-database facades keep
their compatibility path. LLM + Knowledge focused regression: 18 passed; ruff
and diff-check: PASS. Next: safe-TOOL parallel eligibility and pre-dispatch
idempotency/receipt RED.

225.7.3 safe TOOL parallel wave: RED -> GREEN. Only `TOOL_CALL` nodes with
`parallelSafe`, the receipted idempotent MCP adapter method, and the existing
stable run/node key can enter an otherwise-ready parallel wave. The key is
injected into a transient runtime node config before dispatch, and the adapter
receipt is preserved in node evidence. No adapter capability means the whole
Tool wave stays serial; no new retry was added. Focused LLM/Knowledge/Tool
regression: 20 passed; ruff and diff-check: PASS. Next: timeout fail-fast RED.

225.7.4 timeout and late-fence: RED -> GREEN. The parallel-wave controller
uses each prestarted node's existing timeout policy deadline. On expiry it
fails that node, marks remaining active nodes cancelled, trips a shared wave
cancellation event, does not wait for uncooperative worker calls, and returns
the error to terminal Workflow failure. Late worker output has no parent commit
path; LLM delta callbacks are additionally fenced. Tests prove cancellable LLM
peers see cancellation and a blocking Knowledge peer cannot complete after the
terminal failure. Focused LLM/Knowledge/Tool/error-routing regression: 26
passed; ruff and diff-check: PASS. Next: structured failure projection RED.

225.7.5 structured terminal failure and Chatflow turn isolation: RED -> GREEN.
Workflow result data retains its existing envelope and string `error`, adding
sanitized `failure` and `errorCode` (`WORKFLOW_NODE_TIMEOUT` or
`WORKFLOW_NODE_FAILED`); the matching terminal event carries the same object.
RuntimeLab retains terminal `error` and adds `failure`. A Chatflow failed turn
now records session status `failed`; the next normal message gets a new run,
returns its own answer, and replaces the session state without replaying the
failure. The Customer Assistant envelope was not changed. Next: worker lease
takeover safe-Tool idempotency proof.

225.7.6 lease takeover safe-Tool idempotency: RED -> GREEN. A deterministic
crash after the provider accepts a Tool operation but before the Runtime V2
node commit exposed that a resumed one-node serial path lost the prior
parallel-safe key. Explicitly `parallelSafe`, receipted MCP Tools now inject
the existing stable run/node/type key in that recovery path too. The adapter
deduplication proof observes two provider submissions for the crashed Tool but
exactly one side effect per Tool key; no ledger, migration, or retry expansion
was introduced. 225.7 aggregate focused regression: 41 passed. CA focused
compatibility suite is green (37 focused test dots; test runner emitted no
summary line). Next: static/broad/UI gates and fresh independent review.

225.7.7 Reviewer delta-terminal race: RED -> GREEN. The first independent
review found that an LLM delta could pass its in-memory cancellation check,
block, then be persisted after `workflow_run_failed`. A deterministic test now
does exactly that: it holds the callback after its pre-check, lets the 80ms
wave timeout terminalize the run, then releases it. The old path wrote
`llm_delta` at sequence 11 after terminal failure at sequence 10. Delta
persistence now takes a `RUNNING` `SELECT ... FOR UPDATE` fence in the same
transaction as its event append. If the terminal transition won, the event is
dropped; if the delta owns the run lock first, terminal state waits for the
event commit and follows it. The focused 225.7 suite is now 42 passed; ruff
and diff-check pass. The production `McpFacade` has no native idempotent
receipt API, so it remains intentionally serial rather than being presented
as a real safe-Tool parallel provider. The affected broad integration rerun is
PASS: JUnit reports 152 tests with 0 failures, 0 errors, and 0 skipped in
244.523s. The independent closure review is PASS: it found no 225.7 P0/P1/P2,
and verified the durable delta/terminal fence, safe-McpFacade serial fallback,
8 parallel-wave tests, 13 related failure/CA tests, ruff, and diff-check.
Redis XADD ordering across separate processes remains an existing event-bus
boundary outside this contract; no event-bus redesign was claimed. Slice 225.7
is closed; Spec 225 acceptance remains open.

225.8 contract confirmed by user after the residual impact was explained.
Scope is intentionally read-side only: sort/deduplicate existing Redis stream
records by durable sequence, and reconcile a live cursor gap through a fresh
short-lived durable backlog before SSE projection. It must retain the normal
Redis realtime fast path and must not add a migration, broker, queue,
distributed publisher lock, new write-side protocol, or public API change.
The original RED exposed Redis `[2, 1, 1]` publication order and a terminal
sequence 2 projected before durable sequence 1. A same-slice follow-up RED
also exposed an internal live-batch gap `[1, 3]`. The repair now normalizes
Redis by sequence and treats any discontinuity from the cursor as a fresh
durable-backlog read. Focused proof is 12 passed; V2/Redis/CA composition is
JUnit 52 tests, 0 failures/errors; RuntimeLab broad regression is JUnit 158
tests, 0 failures/errors/skips. Ruff and diff-check pass. Browser mock UAT,
frontend targeted/full tests, and production build pass; full mypy remains the
known 165-error/23-file repository baseline, with no diagnostic at the new
225.8 helper locations. Fresh independent Reviewer: PASS, no P0/P1/P2. It
verified sequence sorting/deduplication before count, leading/internal-gap
fresh recovery, contiguous Redis-only projection, no-predecessor fallback, and
scope exclusion; it reran focused 12 passed, Ruff, and diff-check. Slice 225.8
is closed. Next: await explicit user direction for the separate commit/merge or
next contract.

225.7 verification sweep: current vertical regression is 20 passed; RuntimeLab
unit/contract broad gate is 134 passed plus 124 subtests; RuntimeLab/integration
broad JUnit is 152 tests with 0 failures/errors/skips; current RuntimeLab
Chatflow E2E is 2 passed. Frontend targeted gate is 24 tests, full frontend is
114 files / 467 tests, production build is PASS, and mocked Browser SSE
reconnect UAT is PASS with artifact output. Ruff and diff-check are PASS. Mypy
remains a 165-diagnostic repository baseline across 23 files; a type-only
follow-up removed the three new helper variance diagnostics. Next: fresh
independent Reviewer verdict; do not close without it.

Known baseline evidence (audit, not closure): targeted adapter 21 passed,
async-ref integrations 4 passed, worker gateway/entry 4 passed; legacy
RuntimeLab message endpoint has no SSE consumer; resume can wait inline; LLM
delta is post-completion synthetic. Two legacy E2E failures assert the removed
execution-state mirror and require a Spec 216-compatible correction in 225.5.

Verifier status:
- 225.7 contract gate: PASS (user confirmed parallel/fail-fast scope and
  turn-scoped Chatflow failure semantics on 2026-07-15);
- 225.7 failure/degradation/takeover focused gate: PASS (42 tests; Workflow
  failure result/event, RuntimeLab SSE error compatibility, Chatflow next-turn
  isolation, and post-crash lease takeover receipt proof);
- isolated worktree hygiene: PASS at base 828782ce;
- loop hook capability: N/A (not present in base); manual RED log required;
- 225.1 contract and integration: PASS (3 focused tests); ruff and diff-check:
  PASS; mypy: baseline-blocked (142 transitive errors, no new stream diagnostic);
- 225.2 provider callback: PASS (15 targeted regressions); durable chunk-before-
  completion and non-stream no-fake-delta proof recorded;
- 225.3 durable resume: PASS (51 focused tests); RuntimeLab wires a resume
  queue, returns refs without request-side execution, and the standalone worker
  claims the idempotency-keyed resume job;
- 225.4 UI stream: PASS (23 focused frontend tests, production build, and
  mocked browser UAT); provider chunks merge in place and reconnect resumes at
  the durable cursor without JSON fallback.
- independent Reviewer: PASS (resume cursor and retry-race follow-up);
- 225.7 closure Reviewer: PASS; 8 parallel-wave tests and 13 related
  failure/CA tests passed, plus ruff and diff-check. The affected broad
  integration rerun is PASS (JUnit: 152 tests, 0 failures/errors/skips,
  244.523s);
- 225.6 independent Reviewer: PASS after the real `ProviderBackedOpenAIChatClient`
  HTTP-stream cancellation seam was added and fresh-context closure review
  found no P0/P1;
- Browser mock UAT: PASS; live-provider UAT: PASS (`qwen/qwen3.5-27b`,
  RuntimeLab -> Runtime V2 -> OpenRouter, 2026-07-14).
