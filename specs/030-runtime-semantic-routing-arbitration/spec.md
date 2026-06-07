# Spec 030: Runtime Semantic Routing Arbitration

## Goal

Extend the isolated runtime lab from spec 029 with mock semantic candidate
recall and constrained intent arbitration, while keeping all execution on mock
SOPs and the existing `runtime_lab` kernel.

The purpose is to prove the routing control plane before connecting real
Chatflow, FAQ, RAG, Agent, or human handoff systems.

## Dependency

This spec starts only after `029-isolated-runtime-router-lab` and its 029.8
kernel hardening gates pass.

Required 029 capabilities:

- persisted runtime session, task, checkpoint, event, and command records;
- idempotent runtime command boundary;
- one active task per session;
- mock SOP adapter;
- suspend, complete, resume offer, and resume task behavior;
- temporary `/api/v1/runtime-lab/...` contract.

## Why This Spec Exists

029 intentionally used strong keyword routing only. That proves task ledger and
resume mechanics, but it does not prove the customer-service routing pattern
needed for real aviation SOP traffic:

- a user may ask to start a new SOP without using exact keywords;
- a user may refer to a suspended task indirectly;
- an active SOP must not collect slots when the user is actually asking to
switch, resume, or clarify another task;
- a small NLP/LLM classifier should see only a finite candidate set, not every
SOP and document in the product;
- high-confidence shallow signals should exit early, while low-confidence or
conflicting signals should be escalated to constrained arbitration.

This spec adds that funnel inside the isolated lab with deterministic mock
recall and mock classifier behavior.

## Product Boundary

In scope:

- candidate model for routeable targets;
- score evidence for keyword and mock semantic recall;
- finite candidate recall for:
  - active task continuation;
  - suspended task resume;
  - mock SOP start;
  - explicit clarify/no-match outcomes;
- constrained classifier interface with deterministic fake implementation;
- policy gate that decides early exit, classifier escalation, clarify, or
  reject behavior;
- API debug evidence showing candidates, scores, classifier input/output, and
  policy decision;
- active-SOP sensitive behavior:
  - no active task can start a high-confidence SOP early;
  - active task with competing candidates must use constrained arbitration;
  - non-interruptible active task still rejects unsafe switch;
- tests and evidence for all gates.

Out of scope:

- real embedding service;
- real BM25, ES, rerank, or vector database;
- real LLM provider call;
- real Chatflow SOP execution;
- real FAQ answer routing;
- real RAG answer routing;
- Knowledge/Clarification Agent execution;
- human handoff policy;
- frontend UI;
- final product API renaming such as `/chat` or `/query`.

FAQ and RAG candidates may be represented only as future extension seams. They
must not be passed into the 030 constrained SOP classifier because 033 owns the
real answer/fallback policy.

## Core Principles

- The route control plane remains separate from SOP execution.
- SOP nodes remain responsible for validating business slot values.
- Keywords and mock semantic recall produce candidates and score evidence; they
  do not become the final answer in active-SOP conflict cases.
- The constrained classifier sees only finite candidates already recalled by
  cheap layers.
- The classifier must not invent a SOP, suspended task, or action that is not in
  the candidate set.
- Policy gate is the final controller. It may accept shallow evidence, require
  classifier arbitration, clarify, reject switch, continue active SOP, or start
  a SOP.
- No product module depends on `runtime_lab`.

## Routing Ladder

030 uses this lab routing ladder:

```text
Runtime command validation and idempotency
  -> load session/task context
  -> explicit cheap signals
  -> mock candidate recall
  -> early policy gate
  -> constrained classifier when needed
  -> final policy gate
  -> mock SOP adapter execution or clarify/reject response
```

### Runtime Command Validation

Reuses the 029.8 service/kernel boundary:

- reject missing session before side effects;
- replay duplicate idempotency key with the same request hash;
- reject duplicate idempotency key with a different request hash;
- preserve event sequence and one-active-task invariant.

### Explicit Cheap Signals

The router detects strong text signals before semantic recall:

- resume phrases such as `continue`, `resume`, `继续`, `继续刚才`;
- strong mock SOP keywords from the manifest;
- exact ordinal or task references when a resume offer exists;
- explicit refusal or no-op phrases that should not mutate task state.

The cheap layer can create high-confidence candidates. It should not perform
business entity extraction for SOP slot filling. Slot filling remains inside the
SOP adapter or the future Chatflow adapter.

### Mock Candidate Recall

Recall is deterministic in 030 and can use simple lexical similarity fixtures.
It must mimic the shape of future keyword/BM25/vector recall without requiring
external services.

Required candidate sources:

- `ACTIVE_TASK_CONTINUE`: the currently active task, if present;
- `SUSPENDED_TASK_RESUME`: suspended tasks and their resume summaries;
- `SOP_INTENT`: mock SOP manifests;
- `CLARIFY`: no safe target;
- `REJECT_SWITCH_CONTINUE_ACTIVE`: active non-interruptible task protection.

Each candidate includes:

- `candidate_id`
- `candidate_type`
- `target_id`
- `display_name`
- `source`
- `score`
- `score_breakdown`
- `matched_terms`
- `risk_level`
- `requires_classifier`
- `reason`

## Score Semantics

Scores are routing confidence signals, not statistical confidence intervals.
They are calibrated policy inputs.

Minimum deterministic scores:

- exact strong keyword match: `1.00`;
- configured alias match: `0.85`;
- phrase-level resume match: `0.90`;
- mock semantic close match: `0.70` to `0.84`;
- weak lexical overlap: `0.40` to `0.69`;
- no match: below `0.40`.

Policy thresholds start as constants:

- `strong_accept_threshold = 0.90`;
- `semantic_accept_threshold = 0.78`;
- `classifier_required_below = 0.90`;
- `candidate_margin_threshold = 0.12`.

Thresholds are lab constants in 030. Runtime configuration UI is deferred.

## Early Exit Rules

No active task:

- one unambiguous SOP candidate above `strong_accept_threshold` may start a SOP
  without classifier arbitration;
- if top candidates conflict or margin is too small, use classifier;
- if no candidate is reliable, clarify.

Active task:

- exact resume-offer phrases may resume the offered suspended task;
- different SOP start, suspended task resume, and active continuation conflicts
  must use constrained classifier unless the signal is an explicit resume offer
  accept;
- if classifier selects a different SOP while the active task is
  non-interruptible, reject switch and continue active prompt;
- if classifier selects active continuation, pass the message to the mock SOP
  adapter;
- if classifier cannot decide, clarify without mutating SOP state.

This captures the intended asymmetry: active SOP routing is more conservative
than no-active routing.

## Constrained Classifier Contract

The classifier receives:

- latest user message;
- compact session state;
- active task summary, if any;
- suspended task summaries, if any;
- top-k SOP candidates;
- top-k suspended task candidates;
- allowed action enum;
- policy thresholds.

The classifier returns JSON only:

```json
{
  "selected_action": "START_SOP",
  "selected_candidate_id": "sop:refund_ticket",
  "confidence": 0.82,
  "rationale": "User asks to refund a ticket.",
  "needs_clarification": false,
  "clarification_question": null
}
```

Allowed actions:

- `CONTINUE_ACTIVE_SOP`
- `START_SOP`
- `SUSPEND_AND_START`
- `RESUME_TASK`
- `CLARIFY`
- `REJECT_SWITCH_CONTINUE_ACTIVE`

030 uses a deterministic fake classifier. It must enforce that
`selected_candidate_id` belongs to the provided finite candidate set unless the
action is `CLARIFY`.

## API Evidence

Existing runtime-lab message responses keep their envelope and core shape, but
add debug fields under the route decision payload:

- `candidates`
- `candidateSources`
- `policyGate`
- `classifierRequest`
- `classifierResult`
- `finalDecision`

The API remains temporary and debug-oriented.

## Acceptance Criteria

- No active task plus one strong SOP candidate starts the SOP without classifier
  use.
- No active task plus conflicting SOP candidates calls the classifier once.
- Active task plus a competing SOP candidate calls the classifier before
  mutating the SOP.
- Active task plus classifier-selected current task continues the SOP.
- Active interruptible task plus classifier-selected different SOP suspends and
  starts.
- Active non-interruptible task plus classifier-selected different SOP rejects
  switch and preserves the active task.
- Suspended task resume can be selected from a finite suspended-task candidate.
- Classifier cannot select a target outside the provided candidates.
- Idempotent replay still returns the same candidate and classifier evidence.
- Existing 029 runtime-lab E2E still passes.

## Completion Gate

030 is complete only when:

- all 030 unit, integration, contract, and API E2E tests pass;
- targeted `ruff` and `mypy` gates pass;
- full backend pytest passes or any unrelated failure is documented;
- evidence is saved under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/`;
- no real Chatflow, Agent, FAQ, RAG, or handoff module is called;
- one git commit contains only 030 spec and implementation changes.
