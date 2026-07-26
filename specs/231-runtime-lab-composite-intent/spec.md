# Spec 231: RuntimeLab Composite Intent Resolution

Status: accepted on 2026-07-26; depends on Spec 230 Goal Gate.

## Problem

RuntimeLab can recall more than one finite SOP candidate, but its route contract
still produces one final action and one target. For the current regression
phrase `"我想退费并开发票"`, the constrained classifier may select
`invoice_apply` and immediately start that task. The `refund_ticket` component,
the relationship between the two requests, and the user's preferred execution
order are lost.

This is not only a recall-quality problem. Even perfect Top-K recall cannot
represent a user turn that contains multiple actionable intents. Silently
flattening such a turn into one task makes evaluation look successful while
discarding user intent.

## Intended Outcome

Represent bounded composite intent explicitly, preserve every supported atomic
component, and resolve its relationship before any task mutation. RuntimeLab
continues to execute at most one active SOP at a time; composite detection does
not introduce a parallel workflow engine.

## Scope

### In Scope

- deterministic detection of two or more supported atomic candidates;
- an additive `CompositeIntentResult` containing components and relation;
- relations `AND` and `THEN`;
- constrained classifier output that can select only canonical candidates;
- targeted sequencing clarification for multiple transactional intents;
- a safe answer-then-offer path for one consultation plus one transaction;
- a bounded pending composite route plan in the RuntimeLab route ledger;
- explicit resolution, expiry, replay, and audit evidence;
- re-evaluation by the Spec 230 execution gate when a component is chosen;
- evaluation, API/UI projection, and Browser UAT for composite cases.

### Out Of Scope

- concurrent execution of two active SOPs;
- a generic planner, DAG engine, workflow table, or orchestration DSL;
- arbitrary model-generated intents, targets, relations, or steps;
- copying child Chatflow execution state into RuntimeLab;
- cross-session composite plans;
- changing one-active/one-suspended task limits;
- production execution, live provider calls, merge, or deployment.

## Composite Intent Contract

```text
CompositeIntentResult
  detected: bool
  components[]
    candidate_id
    intent_id
    confidence
    risk_class
    evidence_refs[]
  relation: AND | THEN
  primary_component_id: nullable
  clarification_question: nullable
```

Rules:

- every component must resolve to one fused canonical candidate from Spec 229;
- duplicate canonical IDs are rejected;
- the classifier cannot add an intent, target, prerequisite, or execution step;
- at least two distinct atomic components are required for `detected=true`;
- components use stable candidate order unless an explicit supported sequence
  cue establishes `THEN`;
- ambiguous conjunction defaults to `AND` plus clarification, never an inferred
  execution order;
- conflicting classifier fields fail closed to `CLARIFY`;
- detection and persistence of a pending plan perform zero task, adapter, or
  child Runtime V2 mutation.

Deterministic connector and clause cues establish the component proposal before
optional constrained arbitration. The local deterministic path is the required
gate; live LLM arbitration is not required.

## Resolution Policy

### Two Or More Transactional Intents

Return `CLARIFY` with:

- additive `clarificationReason = COMPOSITE_INTENT`;
- additive `compositeIntent`;
- a targeted question asking which supported component should be handled first;
- zero task/adapter mutation.

After the user explicitly chooses a component, RuntimeLab rechecks current
candidates, state version, prerequisites, permission, confirmation, and the
Spec 230 execution gate. The stored plan is evidence, not authority.

### Consultation Plus One Transaction

If the consultation answer is deterministic and read-only, RuntimeLab may
answer it in the current turn only after the Spec 230 read gate allows it, then
return an additive offer for the transaction. The transaction starts only after
explicit acceptance and a fresh execution-gate decision.

If the consultation requires uncertain generation, external access, or a
stateful action, return targeted clarification instead.

### Active Or Suspended Tasks

Composite resolution does not bypass existing task policy:

- one active task and at most one suspended task remain authoritative;
- current active/suspended state is re-read at resolution time;
- a stale plan returns `STALE_RETRY` or a new clarification;
- no component is silently dropped because a task slot is unavailable.

## Pending Composite Plan

The RuntimeLab route ledger records bounded events:

```text
COMPOSITE_INTENT_DETECTED
COMPOSITE_INTENT_RESOLVED
COMPOSITE_INTENT_EXPIRED
```

The detected event stores canonical component references, relation, policy and
catalog versions, state version, clarification/offer, and a stable plan hash.
It contains no raw sensitive slot values.

The pending plan expires at session end or after three subsequent user turns,
whichever comes first. Idempotent command replay returns the same plan and
assistant response. Resolution is single-purpose and cannot be replayed across
session, tenant, state version, or changed component set.

Use existing route-event persistence unless a RED proves it cannot provide
single-session replay and expiry. A new generic plan table is forbidden without
a separately accepted contract.

## Public Compatibility

- current `/api/v1/runtime-lab/...` routes, envelopes, and SSE
  `delta|done|error` semantics remain;
- existing route action values remain valid;
- `compositeIntent`, `clarificationReason`, and `nextActionOffer` are additive
  and nullable;
- single-intent turns preserve current behavior after Specs 228-230 gates;
- older clients may render the assistant text while ignoring new evidence;
- route logs/evaluation never expose raw sensitive slot values.

## Required Evaluation Cases

- `"我想退费并开发票"` returns both `refund_ticket` and `invoice_apply`,
  asks for order, and starts neither;
- explicit order such as `"先退票，再开发票"` preserves `THEN`;
- a user choice resolves only the selected first component;
- consultation plus transaction answers safely, then offers the transaction;
- unknown or disabled clause is not invented as a component;
- duplicate source observations do not create duplicate components;
- stale, expired, cross-session, and changed-candidate resolution fail closed;
- single-intent and existing suspend/resume scenarios remain green.

## Slices

1. `231.1` atomic component model and deterministic detection.
2. `231.2` sequencing clarification and pending ledger plan.
3. `231.3` consultation-plus-transaction offer and resolution.
4. `231.4` regression, Browser UAT, and Goal Gate.

## Success Predicate

Spec 231 is satisfied only when:

1. the current composite regression retains both atomic components and no
   longer silently starts `invoice_apply`;
2. every detection/clarification/offer turn performs zero task, adapter, and
   child-effect mutation;
3. resolution requires explicit user input and a fresh Spec 230 gate;
4. the classifier cannot invent candidates or execution order;
5. replay, expiry, stale-state, and cross-session negative cases pass;
6. single-intent, active/suspended, API, and SSE compatibility remain green;
7. Unit, Integration, Contract, E2E, Browser UAT, Docs, independent Checker,
   and Reviewer gates pass.

## Goal Controls

- max attempts: 3 per slice;
- inherits the outer 21-day TTL;
- provider budget: 0;
- on exhaustion: `WAITING_HUMAN`;
- review context: standard;
- independent Checker and Reviewer are mandatory.

## Human Gates And Authority

Accepted by the user on 2026-07-26 as the final contract in the Spec 228-231
sequence. Slice commits and branch push are authorized.

Not authorized: merge, PR, deployment, production writes, live/paid provider
calls, or expansion into a generic orchestration engine.
