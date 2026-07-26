# Spec 228: Runtime Policy Replay Integrity And Uncertainty Enforcement

Status: accepted on 2026-07-26; implementation not started.

## Problem

RuntimeLab already has finite candidate arbitration, policy profiles, decision
logs, golden-matrix replay, and release governance. Two accepted contracts are
not enforced by the current production path:

1. Runtime policy replay uses a parallel string-matching helper instead of the
   decision engine used by `RuntimeLabService`.
2. `classifierMinConfidence`, `needs_clarification`, and
   `clarification_question` are not enforced consistently for real LLM output.

This permits false-green evaluation and a low-confidence LLM selection to reach
task mutation. It also replaces a model-generated targeted clarification with a
fixed airline intent menu.

## Baseline Evidence

- `app/modules/runtime_policy/domain/governance.py` calls
  `_candidate_decision()` for golden and historical replay. That helper does
  not execute candidate recall, constrained arbitration, or Policy Gate.
- `FakeConstrainedIntentClassifier` applies `classifierMinConfidence`;
  `LlmConstrainedIntentClassifier` only validates action/candidate membership.
- the environment bootstrap profile sets `classifierMinConfidence = 0.0`;
- `RouteDecision` has no targeted clarification field;
- `RuntimeLabService` returns a fixed clarification menu;
- `_recover_clarify_result()` may replace an explicit real-LLM clarification
  with another finite candidate;
- RuntimeLab Integration/Contract gates require MySQL 8. At contract creation,
  `127.0.0.1:3306` was unavailable.

## Intended Outcome

Runtime policy evaluation must exercise the same decision implementation used
by RuntimeLab, and every uncertain classifier result must pass a server-owned
uncertainty gate before any task or child Chatflow mutation.

## Scope

### In Scope

- a versioned `RouteEvalCase` and deterministic report contract;
- `required` versus `known_gap` case status;
- an injected real-route replay port used by runtime policy governance;
- removal of the parallel `_candidate_decision()` truth path;
- parity tests between evaluation decisions and RuntimeLab message handling;
- server-side confidence, result-coherence, and clarification enforcement;
- additive `clarificationQuestion` route evidence and public response support;
- targeted clarification reply with bounded fallback;
- bootstrap minimum confidence `0.60`;
- release validation rejecting a zero confidence threshold for new activation;
- deterministic, zero-provider-call default gates.

### Out Of Scope

- candidate fusion or Top-1/Top-2 margin policy, owned by Spec 229;
- multi-turn RouteContextSnapshot, Intent Catalog, or Intent RAG;
- permission or side-effect authorization, owned by Spec 230;
- composite-intent behavior, owned by Spec 231;
- mandatory live LLM evaluation;
- replacing RuntimeLab with a generic planner;
- database tables unless the RED proves existing evaluation JSON cannot retain
  the required report.

## Route Evaluation Contract

Each case records:

```text
case_id
case_version
status: required | known_gap
turns[]
initial_route_context
enabled_intent_ids
policy_snapshot
classifier_fixture
expected:
  recalled_candidate_ids
  final_action
  target_id
  clarification_question
  mutates_task_state
```

The report records candidate Recall@K, action/intent confusion data,
state-transition correctness, clarification outcomes, elapsed time, and
provider usage. A `known_gap` is visible and cannot contribute to a passing
required-case count.

The evaluator may use a pure decision component only if
`RuntimeLabService` delegates to the exact same component. At least one MySQL
integration parity test must run the public message path. A parallel heuristic,
fixture-only decision helper, or expected-value echo is forbidden.

## Uncertainty Contract

Before `PolicyGate.classifier_decision()`:

```text
needs_clarification == true
OR confidence is non-finite or outside 0..1
OR confidence < classifierMinConfidence
OR action/result fields are incoherent
=> CLARIFY
=> no RuntimeLab task mutation
=> no child adapter invocation
```

Result coherence:

- non-CLARIFY requires an allowed action, an in-pool candidate, and
  `needs_clarification = false`;
- CLARIFY requires `needs_clarification = true`;
- a targeted question is stripped, limited to 256 characters, and must be
  non-empty after normalization;
- an invalid/missing question falls back to the existing generic menu;
- an explicit uncertainty result cannot be recovered into a task-mutating
  action;
- technical classifier failure may use an existing deterministic fallback only
  when that fallback independently passes the same uncertainty policy.

Existing profiles remain readable. New profile activation must reject
`classifierMinConfidence <= 0`. No existing active profile is silently edited.

## Public Compatibility

- existing `/api/v1/runtime-lab/...` routes and envelopes remain unchanged;
- existing route actions remain valid;
- `clarificationQuestion` is additive and nullable;
- SSE `delta|done|error` semantics remain unchanged;
- idempotent replay returns the same question and route evidence;
- no secrets or raw provider payloads enter evaluation reports.

## Slices

1. `228.1` real-route evaluation contract and runner.
2. `228.2` runtime policy governance replay integration.
3. `228.3` server-owned uncertainty enforcement.
4. `228.4` targeted clarification API and browser-visible behavior.
5. `228.5` Contract A regression and Goal Gate.

## Success Predicate

Spec 228 is satisfied only when:

1. faulting the shared decision implementation makes replay fail;
2. every required case executes the shared production decision path;
3. known gaps remain explicit and cannot be counted as PASS;
4. low/invalid confidence and `needs_clarification=true` cause CLARIFY with
   zero task/adapter mutation;
5. targeted clarification survives API, persistence/replay, and UI projection;
6. bootstrap minimum confidence is `0.60`, while legacy profiles are not
   silently rewritten;
7. focused Unit, Integration, Contract, E2E, Browser UAT, Docs, Checker, and
   Reviewer gates pass.

## Goal Controls

- max attempts: 3 per slice;
- TTL: 21 calendar days from first implementation write;
- provider budget: 0 live/paid calls;
- on exhaustion: `WAITING_HUMAN`;
- review context: standard;
- independent Checker and Reviewer are mandatory.

## Human Gates And Authority

Accepted by the user on 2026-07-26:

- create and use an isolated `codex/` branch/worktree;
- implement the four-contract Spec 228-231 sequence;
- create slice commits and push the branch.

Not authorized:

- merge, PR creation, deployment, production migration/application;
- live/paid provider calls;
- weakening tests, replacing real replay with synthetic truth, or treating an
  unavailable MySQL/browser gate as PASS.
