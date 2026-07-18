# ADR 0005: Shared Agent Harness Over A Domain-neutral Runtime Job Substrate

## Status

Accepted for Spec 226 on 2026-07-18.

## Context

Hify already has a durable `runtime_jobs` table, atomic claim, lease token,
heartbeat renewal, retry/backoff, DLQ, crash takeover tests, Runtime Ops views,
and a standalone worker. The schema is owner-oriented, but the repository,
worker builder, routes, and CLI are implemented under `workflow`.

AI Assistant separately owns a router-level `ThreadPoolExecutor`, an in-flight
set, run claim/checkpoint state, and an explicit `/worker/process` endpoint.
The frontend calls that endpoint after `messages/async`, even though the backend
also schedules the same run.

Directly importing the Workflow worker into AI Assistant would make an Agent
product depend on Workflow composition. Building another Agent job queue would
duplicate proven HA behavior.

Customer Assistant was intended to consume the AI Assistant Harness
capabilities, but the current code instead implements a separate
`ControlledReActCore`, `RestrictedReactWorker`, worker registry, and tool policy.
AI Assistant also imports a Customer Assistant harness helper from its tool
registry. Keeping these loops separate duplicates execution invariants and
reverses the intended dependency direction.

Customer Assistant must not import the AI Assistant product Module. Reusable
execution semantics need a product-neutral public Module with two real Adapters.

## Decision

1. Promote only the generic job state machine, repository, lease/heartbeat,
   retry/DLQ behavior, handler registry, and worker loop into a domain-neutral
   runtime module.
2. Keep Workflow, Chatflow, and AI Assistant execution handlers inside their
   domains. The application composition root registers them.
3. The runtime job core must not import a business module.
4. AI Assistant `messages/async` enqueues a durable `AI_ASSISTANT` job. A
   standalone worker consumes it; the request thread does not execute ReAct.
5. Evolve runtime job uniqueness to include owner type, because numeric run ids
   come from independent domain tables.
6. Keep delivery at-least-once. Lease fencing plus the Spec 224 durable
   operation ledger protects duplicate side effects and ambiguous `UNKNOWN`.
7. Extract a public deep Agent Harness Module. Its single execution Interface
   owns bounded ReAct progression, planning transitions, tool governance,
   context/memory ordering, permission/approval transitions, checkpoints,
   cancellation, and standard events. AI Assistant and Customer Assistant are
   product Adapters; their storage, business-task, UI, model, and tool
   implementations remain private.
8. Preserve `/worker/process` only as a migration shim while known consumers
   move to durable enqueue. Delete it only after the Spec 226 compatibility gate.
9. Keep Agent Execution as a smaller public Module used by Agent Harness for
   parent-child identity, lifecycle status, durable refs, capabilities, and
   provider operations. It does not duplicate Harness execution semantics.
10. Apply the same extraction rule to every reused capability: shared invariants
   with two real Adapters become a deep public Module; one-off logic stays
   private. Catch-all `common`, `shared`, or `utils` packages are forbidden.

## Options

### A. AI Assistant Imports Workflow RuntimeJobWorker

Rejected. It is fast initially but reverses the desired dependency direction,
forces Workflow composition into Agent execution, and leaves the generic table
owned by one business module.

### B. Build A Separate Agent Queue And Worker

Rejected. It duplicates claim, lease, retry, DLQ, Ops, fault tests, and
standalone process behavior, increasing correctness and operating cost.

### C. Keep Separate Product Harness Loops

Rejected. AI Assistant and Customer Assistant already duplicate bounded ReAct,
tool gating, observation, lifecycle event, and terminal-state semantics. Keeping
them separate loses locality and makes security/HA fixes diverge.

### D. Customer Assistant Imports AI Assistant

Rejected. AI Assistant is a product Adapter with repository, workspace, Web and
shell semantics. Importing it from Customer Assistant creates product coupling
and prevents the public Harness Interface from remaining stable.

### E. Promote Agent Harness, Agent Execution And Runtime Substrate

Accepted. Agent Harness provides execution leverage through one product-neutral
Interface. Agent Execution provides child lifecycle, and Execution Substrate
provides durable HA scheduling. Product and business differences stay behind
Adapters.

## Consequences

Positive:

- one HA job mechanism and one Ops surface；
- one Harness execution state machine for AI Assistant and Customer Assistant；
- no AI Assistant -> Workflow dependency；
- no Customer Assistant -> AI Assistant product dependency；
- security, checkpoint and event fixes gain cross-product locality；
- process restart/takeover becomes possible for AI Assistant；
- in-process worker state and frontend kick call can be removed。

Costs:

- Alembic migration and owner-aware repository/API tests；
- staged compatibility Adapters while two existing loops converge；
- composition root and compatibility imports during migration；
- worker must restore trusted AI Assistant scope without an HTTP request；
- `/worker/process` needs an explicit compatibility lifecycle。

## Guardrails

- no new broker is introduced；
- raw secrets never enter runtime job payload；
- runtime core cannot dispatch by importing domains dynamically；
- Agent Harness cannot import AI Assistant、Customer Assistant、Workflow、Web or
  infra Adapters；
- Customer Assistant cannot import the AI Assistant product Module；
- Agent Execution cannot duplicate ReAct、tool、memory or permission semantics；
- product business-task、storage、UI and tool implementations remain behind
  their Adapters；
- every public Module must pass the deletion test and have at least two real
  Adapters or an already domain-neutral infrastructure invariant；
- no catch-all `common`、`shared` or `utils` package；
- unknown handler fails to DLQ；
- no fake child running state；
- no permanent old/new worker dual path；
- production migration/deploy is outside Spec 226 authorization。

## Revisit Conditions

Broaden Agent Harness or Agent Execution only when two independent Adapters
require the same new invariant and Interface-level tests prove it. Similar
naming is not sufficient.

Revisit the runtime substrate choice if measured throughput or scheduling
requirements cannot be met by the existing DB/Redis architecture and an
accepted capacity report justifies a different platform.
