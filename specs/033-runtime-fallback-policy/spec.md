# Spec 033: Runtime Handoff Foundation

## Goal

Add the runtime-lab handoff foundation that every later fallback layer can use.

033 is not the FAQ/RAG/Agent implementation spec. It provides one normalized
control-plane action for human handoff, hard-stop trigger detection, route
evidence, and context snapshot behavior so later specs can escalate safely
without inventing their own side effects.

## Numbering And Dependency

Numbering was rechecked on 2026-06-09. `035` is already used by
Knowledge Retrieval Productization, so the remaining fallback specs continue as
`036` through `040`.

033 starts only after 032 gates pass.

Required 032 capabilities:

- one real Chatflow-backed SOP path;
- stable adapter integration;
- preserved task ledger and checkpoint behavior;
- existing Chatflow regression gates passing.

## Current Code Baseline

Available today:

- `CLARIFY` exists as a route action and classifier action.
- SOP strong trigger templates exist on SOP manifests.
- Runtime-lab explicit signal detection handles SOP triggers, resume phrases,
  and refusal/no-op phrases.
- Existing `handoff` module can create queued tickets.
- Chatflow has `TRANSFER_TO_HUMAN` node support.

Missing today:

- runtime-lab does not expose `HANDOFF_TO_HUMAN`;
- handoff is not an allowed constrained classifier/policy action;
- explicit handoff/safety triggers are not in runtime-lab candidate recall;
- runtime-lab does not emit `HANDOFF_REQUESTED` events or context snapshots;
- later FAQ/RAG/Agent fallback layers cannot escalate through a shared handoff
  policy yet.

## Scope

In scope:

- `HANDOFF_TO_HUMAN` route action and serialized response contract;
- finite candidate/action validation for handoff inside the existing policy
  gate;
- explicit handoff hard-stop trigger detection:
  - user asks for human support;
  - complaint/escalation wording;
  - safety/compliance sensitive wording;
  - unsupported business process wording;
  - repeated low-confidence/clarification failure signal from later specs;
- runtime events for handoff decision/request;
- context snapshot for active task, suspended tasks, route evidence, recent
  transcript, and business refs;
- optional one-way call into the existing `handoff` module.

Out of scope:

- FAQ exact or semantic answering;
- RAG answer generation;
- fallback Agent response generation;
- frontend human-service console;
- autonomous Agent task mutation;
- broad Chatflow internals rewrite.

## Routing Position

033 must run before every non-handoff layer:

```text
033 explicit handoff/safety hard stops
  -> 036 exact/high-confidence FAQ answer gate
  -> 037 semantic FAQ answer gate
  -> SOP/resume constrained arbitration
  -> 038 RAG answer gate
  -> 039 controlled Agent fallback
  -> 040 final E2E acceptance
```

Later layers may propose or trigger handoff only by returning the shared
`HANDOFF_TO_HUMAN` route action. Final handoff execution stays centralized in
the runtime control plane.

## Handoff Contract

The route action payload must preserve enough state for a human agent to
understand the current conversation:

```text
HANDOFF_TO_HUMAN {
  sourceLayer,
  reasonCode,
  userMessage,
  activeTaskSummary,
  suspendedTaskSummaries,
  routeEvidence,
  recentTranscript,
  businessRefs
}
```

Active and suspended SOP state must not be lost or rewritten merely because the
handoff route fires.

## Slice Plan

### 033.1 Handoff Action Contract

Add action/candidate support only. The RED tests must fail until
`HANDOFF_TO_HUMAN` is accepted by classifier validation, policy gate, payload
formatting, and contract serialization.

### 033.2 Explicit Handoff Trigger Templates

Add strong explicit trigger detection for human-support, complaint, compliance,
emergency, and unsupported-process phrases. These triggers are hard stops and
must exit before FAQ/SOP/RAG/Agent layers.

### 033.3 Runtime Handoff Event And Context Snapshot

Route `HANDOFF_TO_HUMAN` into runtime events and, when configured, the existing
handoff service. Preserve active/suspended task summaries, route evidence,
recent transcript, and business refs.

### 033.4 Handoff Policy Regression Gate

Prove existing SOP start/switch/resume behavior still passes and that handoff
does not corrupt active/suspended task state.

## Acceptance Criteria

- `HANDOFF_TO_HUMAN` is a first-class runtime route action.
- Explicit handoff/safety wording exits before FAQ/SOP/RAG/Agent routing.
- Active and suspended task state is preserved when handoff fires.
- Handoff emits auditable route evidence and runtime events.
- Optional existing `handoff` module integration is one-way from runtime-lab.
- Existing 030 routing and 032 Chatflow-backed SOP paths still pass.
- No FAQ/RAG/Agent implementation is introduced in 033.

## Completion Gate

033 is complete only when:

- RED evidence exists for each slice before implementation;
- unit/contract/integration tests for handoff route behavior pass;
- active/suspended state preservation tests pass;
- SOP routing regressions pass;
- browser UAT is executed only if user-visible lab behavior changes;
- evidence is saved under `artifacts/slices/033-runtime-fallback-policy/`;
- `spec.md`, `plan.md`, and `tasks.md` are updated with final evidence;
- one git commit contains only 033 handoff-foundation changes.

## Completion Capability

After 033, every later routing layer can escalate through one normalized human
handoff route. FAQ, RAG, and Agent fallback specs will propose or trigger
handoff through this action instead of creating independent side effects.

## Specification Sign-off

Status: complete.

Completion evidence:

- `033.1/red.txt`, `033.1/unit.txt`, and `033.1/regression.txt`
  cover the first-class handoff action contract.
- `033.2/red.txt`, `033.2/unit-integration.txt`, and
  `033.2/regression.txt` cover explicit hard-stop trigger templates and active
  task state preservation.
- `033.3/red.txt`, `033.3/integration.txt`, and `033.3/regression.txt`
  cover runtime events, context snapshots, optional handoff service integration,
  and user-facing handoff replies.
- `033.4/red.txt`, `033.4/contract.txt`, and `033.4/final-targeted.txt`
  cover the real API contract and runtime-lab/SOP regression gate.
- `033.4/e2e.txt` covers the API e2e regression gate, including explicit
  handoff and existing SOP start/switch/resume/complete behavior.
- `033.4/browser-uat-result.json`, `033.4/uat.md`, and
  `033.4/screenshots/browser-uat-handoff.png` cover the Codex in-app Browser
  Swagger UI UAT. The recorded UAT result has `passed=true`, verifies
  `HANDOFF_TO_HUMAN`, `explicit_signal`, `USER_REQUEST`, `HANDOFF_DECIDED`,
  `HANDOFF_REQUESTED`, and preserved active task state.

Full backend pytest was attempted and documented in
`033.4/full-backend-note.md`; the run reached live provider acceptance tests and
was stopped as an external/live gate. No FAQ, RAG, or Agent fallback behavior is
implemented in 033.
