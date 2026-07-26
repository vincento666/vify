# Spec 230: Runtime Route Execution Boundary

Status: accepted on 2026-07-26; depends on Spec 229 Goal Gate and ADR 0010.

## Problem

RuntimeLab directly dispatches valid route actions into task mutation and child
Chatflow execution. Identity, tenant, permission, risk prerequisites,
confirmation, stale state, and idempotency are not evaluated by an independent
execution gate.

## Intended Outcome

A RouteDecision becomes an execution proposal. No task or external/write effect
can run until the applicable server-owned execution gate returns `ALLOW`.

## Scope

- trusted `RequestContext` for RuntimeLab conversation/session surfaces:
  session create, gateway/session message, message stream, and session
  task/event/Chatflow-trace reads;
- route read/operate/execute permission checks;
- `RouteExecutionProposal`, gate result, and audit evidence;
- task/session version, prerequisite, confirmation, and idempotency checks;
- gate placement before every RuntimeLab task mutation/adapter call;
- immutable authorization receipt propagation to child Chatflow;
- RuntimeLab-owned Runtime V2 side-effect fail-closed enforcement;
- additive API/UI evidence and confirmation UX;
- security threat matrix and fresh-context review.

## Non-goals

- `/route-model/connectivity`, `/fallback-agent`, and other
  configuration/administration access control; those existing surfaces require
  a separate accepted security contract and this Spec must not claim that all
  RuntimeLab web endpoints are authorized;
- platform-wide forced migration for other runtime owners;
- importing AI Assistant product permission implementation;
- production IAM deployment;
- real airline refund/change writes;
- merge/deploy/live-provider work;
- composite intent, owned by Spec 231.

## Route Gate Contract

Inputs:

```text
trusted principal / tenant / permissions
route decision and candidate evidence
session/task version
risk and prerequisites
confirmation receipt
idempotency key
policy/catalog versions
```

Only `ALLOW` can reach mutation. All other outcomes return a compatible
assistant response and additive `executionGate` evidence.

Required invariants:

- every conversation/session surface first requires trusted tenant-scoped
  `runtime_lab:read`;
- `runtime_lab:read` may create the bounded conversation/route audit records
  needed for an interaction, but cannot mutate a task or invoke a child;
- `ANSWER_FAQ`, `ANSWER_RAG`, safe read-only `AGENT_FALLBACK`, `CLARIFY`, and
  `NO_MATCH` require `runtime_lab:read` and perform zero task/child mutation;
- task lifecycle needs `runtime_lab:operate`;
- high-risk external/write effects need `runtime_lab:execute` and confirmation;
- stale session/task version returns `STALE_RETRY`;
- receipt tenant, actor, action, target, input hash, version, and expiry must
  match;
- idempotent replay returns the original gate/turn result;
- `risk_level` never grants permission.

## Confirmation Contract

`REQUIRE_CONFIRMATION` returns a server-issued, bounded receipt associated with
one proposal. Confirmation:

- is explicit, not inferred from classifier confidence;
- expires after 15 minutes or three subsequent user turns;
- is single-purpose and replay-safe;
- cannot be reused cross-tenant, cross-session, cross-target, or after state
  version changes;
- never stores raw secrets.

## Child Side-effect Contract

RuntimeLab-owned child runs set `enforceExecutionGate=true`. Effect
classification is server-owned:

- `API_CALL` is externally material and requires an applicable
  `runtime_lab:execute` authorization;
- `TOOL_CALL` uses server-owned tool capability metadata; write-capable or
  unknown tools require `runtime_lab:execute`, while proven read-only tools may
  use the read authorization;
- `TRANSFER_TO_HUMAN` is externally material and requires the matching
  handoff/execute authorization;
- `EXECUTE_WORKFLOW` and `AGENT_CALL` are delegation boundaries: they propagate
  the immutable authorization and fail closed if requested child capabilities
  exceed it;
- ordinary RuntimeLab response `MESSAGE` and in-run `VARIABLE_ASSIGN` remain
  internal output/state operations. They keep existing idempotency/execution
  records but do not require `runtime_lab:execute`.

Missing/invalid authorization must become deny or proposed-action/wait evidence.
It cannot be recorded as a successful side effect. Existing node idempotency
and execution records remain required.

## Public Compatibility

- current routes/envelopes/SSE semantics remain;
- `executionGate`, confirmation metadata, and denial reason are additive;
- local development keeps mock SOP usability but not real-write permission;
- existing non-RuntimeLab Workflow/Chatflow calls remain unchanged by default.

## Slices

1. `230.1` trusted principal and execution proposal model.
2. `230.2` pre-mutation RuntimeLab gate.
3. `230.3` confirmation, stale state, idempotency, and audit.
4. `230.4` child Runtime V2 side-effect authorization.
5. `230.5` security matrix, Browser UAT, and Goal Gate.

## Success Predicate

- unauthorized/confirmation/stale decisions cause zero task/adapter/effect
  calls;
- authorized decisions preserve existing SOP behavior;
- cross-tenant/state/action receipt misuse always fails;
- RuntimeLab-owned externally material or delegated child effects cannot
  execute without valid authority;
- non-RuntimeLab runtime compatibility remains green;
- independent security Checker and fresh-context Reviewer accept all evidence.

## Goal Controls

- max attempts: 3 per slice, 2 for a repeated security finding family;
- inherits outer TTL;
- provider budget: 0;
- on exhaustion: `WAITING_HUMAN`;
- review context: `fresh-required`.

## Human Gates And Authority

Accepted as part of the user-authorized Spec 228-231 sequence on 2026-07-26.
Slice commits and branch push are authorized.

Configuration/administration endpoint security, production IAM rollout, PR,
merge, deployment, live provider calls, and production writes remain outside
this authority.
