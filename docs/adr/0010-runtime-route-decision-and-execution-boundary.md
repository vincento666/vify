# ADR 0010: Separate Runtime Route Decisions From Execution Authority

## Status

Accepted for Specs 230-231 on 2026-07-26.

## Context

RuntimeLab currently treats a valid `RouteDecision` as sufficient authority to
create, suspend, resume, or continue a task and invoke a child Chatflow adapter.
Candidate `risk_level` is evidence only. RuntimeLab web endpoints do not yet
bind route execution to a trusted principal/tenant/permission decision.

Runtime V2 already supplies idempotency/proposed-action protection for
side-effect-capable nodes, but that protection is not proof that the caller is
authorized. Intent confidence, execution permission, confirmation, and
side-effect idempotency are separate questions.

This decision covers RuntimeLab conversation/session execution surfaces. The
existing route-model connectivity and fallback-agent configuration endpoints
are administrative surfaces that need a separate accepted access-control
contract; this ADR does not claim complete RuntimeLab web authorization.

## Decision

Adopt two explicit gates:

1. trusted, tenant-scoped conversation/session access plus a
   `RouteExecutionGate` before RuntimeLab task mutation or adapter invocation.
2. Runtime V2 side-effect authorization enforcement for RuntimeLab-owned child
   runs before external/write-capable nodes execute.

The route classifier proposes an intent. It never grants authority.

## Trusted Inputs

- host-derived `RequestContext`;
- tenant/org/actor and permissions from that context;
- current RuntimeLab session/task version;
- effective policy/catalog versions;
- candidate risk/prerequisite evidence;
- server-issued confirmation receipt;
- stable idempotency key.

Message body/header fields are not trusted when the host principal adapter is
not in explicit local-development mode.

## Gate Outcomes

```text
ALLOW
DENY
REQUIRE_CONFIRMATION
HANDOFF
STALE_RETRY
```

Every result is auditable. Only `ALLOW` may mutate task state or invoke the
child adapter.

## Permission Model

- `runtime_lab:read`: read answer/route evidence and create the bounded
  conversation/route audit records needed for an interaction, but never mutate
  a task or invoke a child;
- `runtime_lab:operate`: create/continue/suspend/resume task lifecycle;
- `runtime_lab:execute`: permit confirmed high-risk external/write effects.

Explicit local-development context may operate mock/local SOP flows, but it
cannot authorize real external writes. Those remain proposed/confirmation
paths.

## Child Runtime Boundary

An allowed route creates a signed/immutable-in-process authorization snapshot
containing the gate receipt and policy version. RuntimeLab passes it through
the existing runtime invocation authorization payload.

For RuntimeLab-owned child runs with enforcement enabled:

- API calls and handoff are externally material;
- tool capability comes from the server registry, with unknown/write tools
  failing closed;
- nested workflow/agent calls propagate authority and cannot escalate it;
- ordinary response Message and in-run Variable Assign stay internal and do
  not require execute permission;
- externally material nodes require a valid `ALLOW` receipt appropriate to
  their server-derived capability;
- absent/expired/mismatched authorization becomes proposed action/wait or deny;
- idempotency protection still applies after authorization;
- non-RuntimeLab runs retain existing behavior unless their own contract opts
  into the shared enforcement mode.

## Options Rejected

### Treat high classifier confidence as authority

Rejected: classification quality does not prove identity, permission,
prerequisites, or confirmation.

### Reuse AI Assistant internal permission classes directly

Rejected: creates a RuntimeLab -> AI Assistant product dependency.

### Gate only at SOP start

Rejected: a later child side-effect node could outlive or exceed the original
authorization.

### Gate every Hify run immediately

Rejected: breaking scope expansion. Enforcement is opt-in per owning contract,
with RuntimeLab as the first adopter.

## Consequences

- RuntimeLab web composition must receive trusted request context.
- route evidence gains additive execution-gate fields;
- high-risk execution may add a confirmation turn;
- authorization and idempotency have separate receipts;
- security matrix and fresh-context review become mandatory;
- no production permission rollout or deploy is authorized by this ADR.

## Guardrails

- deny/confirmation/stale branches perform zero task/adapter mutation;
- local compatibility cannot become a production bypass;
- authorization payloads contain no secrets;
- stale or cross-tenant receipts fail closed;
- replay cannot reuse a receipt for different input, task version, or effect;
- existing API/SSE envelopes remain compatible.

## Revisit Conditions

- a platform-wide policy module is accepted by another product contract;
- Runtime V2 adopts mandatory authorization for every owner type;
- production identity provider and permission taxonomy change;
- multi-host signed receipts become necessary.
