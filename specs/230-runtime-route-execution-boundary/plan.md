# Plan — Spec 230

## Dependency Direction

```text
core.host.RequestContext
  -> runtime_lab RouteExecutionGate
       -> RuntimeLabService dispatch
       -> authorization receipt
            -> Runtime V2 side-effect enforcement
```

RuntimeLab does not import AI Assistant or Customer Assistant permission
implementations.

## 230.1 Principal, Surface Access, And Proposal

Bind RuntimeLab session create, gateway/session message, stream, and
task/event/Chatflow-trace read endpoints to trusted request context and tenant
scope. `runtime_lab:read` permits bounded conversation/route audit writes but no
task/child mutation. Define permissions and local-development exception
explicitly. Create pure proposal/gate types and audit serialization.

RED: body/header impersonation, cross-tenant session access, missing operate
permission, missing read permission for FAQ/RAG answers, and local real-write
escalation.

Do not touch route-model connectivity or fallback-agent configuration in this
Spec. Record them as an explicit unprotected administrative-surface follow-up;
do not describe Spec 230 as authorization for all RuntimeLab endpoints.

## 230.2 Pre-mutation Gate

Refactor message dispatch only enough to ensure every read answer and mutating
action crosses the applicable gate. Add adapter/mutation counters to read and
negative tests.

Covered actions:

- read-only `ANSWER_FAQ`, `ANSWER_RAG`, safe `AGENT_FALLBACK`, `CLARIFY`, and
  `NO_MATCH` through the read gate with zero task/child calls;
- START_SOP;
- SUSPEND_AND_START;
- RESUME_TASK;
- CONTINUE_ACTIVE_SOP;
- handoff ticket creation;
- any future mutating route action by fail-closed default.

## 230.3 Confirmation And Replay

Create server-owned confirmation receipts using stable proposal hashes and
session/task versions. Prefer existing command/event persistence; introduce a
schema/migration only if durable single-use/expiry cannot be proven otherwise.

Record:

- principal/tenant IDs and permission names, never credentials;
- decision/outcome/reason;
- proposal and state version hashes;
- confirmation and idempotency refs;
- replay/stale status.

## 230.4 Runtime V2 Enforcement

Propagate authorization through existing runtime invocation payload. Add an
owner-aware enforcement hook before externally material or delegated Runtime V2
nodes.

Compatibility:

- RuntimeLab child runs opt in;
- other owner types preserve current behavior;
- idempotency is evaluated after authorization;
- deny/proposed paths emit durable evidence and do not emit success.
- `MESSAGE` response projection and in-run `VARIABLE_ASSIGN` remain internal;
  their existing idempotency/execution-record behavior stays green.

Threat cases:

- missing receipt;
- modified action/target/input;
- expired receipt;
- cross-tenant/cross-session replay;
- stale state version;
- parallel duplicate confirmation;
- resume after cancellation;
- nested workflow effect escalation.
- `AGENT_CALL` capability escalation;
- unknown/write-capable tool represented as read-only;
- ordinary `MESSAGE` or `VARIABLE_ASSIGN` accidentally over-gated.

## 230.5 Verification

- Unit: gate matrix and receipt validation.
- Contract: trusted context, permissions, additive API fields.
- Integration: read-answer, task/adapter/effect call counters and durable audit.
- Runtime V2 regression: side-effect idempotency and non-RuntimeLab owners.
- E2E/Browser: deny, confirmation, allow, stale retry.
- Security: independent Checker plus fresh-context Reviewer.

## Rollback

Opt-in owner enforcement allows safe rollback for non-RuntimeLab callers.
RuntimeLab cannot bypass the route gate through configuration once Spec 230 is
active. Schema changes, if unavoidable, require reversible Alembic migration.

## Risks

- local development exception becomes production bypass;
- receipt replay crosses tenant/state boundaries;
- authorization happens after partial mutation;
- child effect enforcement reports denial as success;
- shared runtime changes regress unrelated owners.

All are mandatory negative-test families.
