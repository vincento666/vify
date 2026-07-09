# Spec 223: Runtime V2 Boundary, Parallel, And Visual Closure

## Background

Specs 213-221 established the Runtime V2 production baseline, but the latest
browser UAT found a contract/evidence mismatch:

- Workflow/Chatflow product boundaries are not explicit enough. Workflow should
  own the full DAG runtime model, while Chatflow should remain a conversational
  runtime with a controlled DAG subset.
- Spec 215 documents concurrent fan-out as complete, but live timing evidence
  shows same-frontier nodes are still executed serially.
- Spec 217 documents all first-class nodes as compatible, but the document does
  not distinguish executor availability from full Workflow/Chatflow UAT evidence.
- Spec 220 provides Runtime Ops basics, but canvas/ops visual evidence does not
  prove parallel wave overlap or Chatflow blocking/resume state.

This spec is a closure spec. It does not rewrite historical spec completion
records. It adds the missing product boundary, implementation correction, and
evidence gates required to make the already-defined Runtime V2 target auditable.

## Goal

Close the Runtime V2 contract gaps for:

- Workflow full DAG execution and visual proof.
- Chatflow conversational blocking/resume execution and visual proof.
- Runtime V2 node compatibility evidence status.
- Product documentation that prevents Workflow parallel-DAG semantics from being
  incorrectly projected onto Chatflow.

## Product Boundary

### Workflow

Workflow is the full production DAG runtime surface.

Workflow must support:

- explicit `allowFanOut` default-port fan-out;
- selected/skipped branch state;
- implicit fan-in/join;
- terminal side-effect leaves;
- true same-frontier parallel execution for eligible runtime nodes;
- durable `runs` refs and node/event/result projections;
- visual evidence of fan-out, selected/skipped edges, join state, and parallel
  wave overlap.

### Chatflow

Chatflow is a conversational, resumable runtime surface.

Chatflow defaults to one active conversational path per turn. Its core contract
is not full parallel DAG execution; its core contract is:

- clear current blocking node;
- pending prompt/checkpoint visibility;
- resume to the correct waiting node;
- no replay of completed nodes;
- no duplicate side effects after resume;
- selected/skipped branch explanation for conditional routes;
- safe final reply selection that excludes side-effect-only branches.

Chatflow may support a controlled DAG subset for background enrichment, but it
must not use Workflow-style parallel wave language as the default user-facing
mental model.

## Non-Goals

- Do not reopen or rewrite historical slice completion records for specs 215,
  217, 220, or 221.
- Do not force Chatflow to provide full Workflow DAG parity.
- Do not introduce a new explicit Join node.
- Do not claim parallel execution from prestarted `RUNNING` events alone.
- Do not add new provider secrets or rely on hidden local credentials for pass
  evidence.

## Required Corrections

### 223.1 Product Boundary Contract

Document Workflow as full DAG runtime and Chatflow as conversational resumable
runtime with a controlled DAG subset.

Acceptance:

- Production target doc states the boundary directly.
- DAG semantics doc states that Chatflow does not default to full DAG parallel
  execution.
- Existing Runtime V2 docs point to this closure spec for the corrected
  evidence boundary.

### 223.2 Workflow True Parallel DAG Scheduler

Eligible same-frontier Workflow nodes must execute concurrently, not only have
their node-run rows prestarted.

Current eligibility is intentionally conservative: this closure slice enables
true parallel execution only for `API_CALL` nodes whose API resource rows can be
preloaded before worker threads run. LLM, Knowledge, Tool, Agent, and Execute
Workflow fan-out remain supported by the existing frontier semantics but are not
treated as thread-safe true-parallel nodes until their executor/session
contracts have explicit evidence.

Acceptance:

- A three-branch slow `API_CALL` fan-out finishes near one branch latency, not
  the sum of branch latencies.
- Event sequences remain monotonic under concurrent completion.
- Node outputs and scoped variables do not cross-contaminate.
- Cancel/deadline behavior remains safe for not-started and running branches.
- Timing evidence includes wall-clock duration and branch start/finish overlap.

### 223.3 Node Compatibility Evidence Matrix

Separate implementation compatibility from UAT evidence.

Acceptance:

- The node compatibility matrix records executor availability separately from
  evidence status.
- Every first-class node has Workflow and Chatflow evidence state:
  `covered`, `partial`, `automated-only`, `not-applicable`, or `missing`.
- Missing or partial evidence has an owning follow-up task.

### 223.4 Workflow DAG Visual Evidence

Workflow canvas and Runtime Ops must visually prove the DAG behavior they claim.

Acceptance:

- fan-out edges are visible;
- selected/skipped edges are distinguishable;
- join nodes show waiting/ready/completed state;
- a parallel wave/timeline view shows overlapping branch execution;
- screenshots are saved from the in-app browser for a published Workflow run.

### 223.5 Chatflow Blocking/Resume Visual Evidence

Chatflow canvas must emphasize the currently blocking node instead of implying
full parallel DAG behavior.

Acceptance:

- The active `WAITING`/`INTERRUPTED` node is highlighted with a looping border
  light animation.
- The animation means "waiting for user/operator input", not "parallel running".
- `prefers-reduced-motion` renders a static high-contrast waiting border.
- The pending prompt and resume target are visible in the debug panel.
- Browser UAT proves resume returns to the same waiting node without replaying
  completed side-effect nodes.

### 223.6 Closure Regression

The final closure must prove the corrected boundaries without regressing the
previous production baseline.

Acceptance:

- Workflow full-DAG tests and Browser UAT pass.
- Chatflow blocking/resume tests and Browser UAT pass.
- Runtime Ops evidence screens show the right product-specific state.
- Existing Runtime V2 baseline gates stay green.

## Evidence Root

```text
artifacts/slices/223-runtime-v2-boundary-parallel-visual-closure/<slice>/
```

## Current Known Evidence

- Parallel UAT report:
  `artifacts/slices/spec213-browser-uat/runtime-v2-parallel-branches/UAT_REPORT.md`
- CODE fan-out run `28799`: succeeded but serialized, `4754ms`.
- API_CALL fan-out run `28800`: succeeded but serialized, `6897ms`.

These runs are evidence of the gap, not pass evidence for true parallel
execution.

## Closure Evidence

Spec 223 pass evidence is recorded under:

```text
artifacts/slices/223-runtime-v2-boundary-parallel-visual-closure/
```

Key evidence:

- `223.4/browser-uat.md`: published Workflow true-parallel DAG browser UAT,
  run `28861`, parallel wave `wave-28861-1`, Runtime Ops screenshot.
- `223.5/runtime-browser-uat.md`: published Chatflow blocking/resume UAT,
  runs `28862` and `28863`, waiting highlight, UI resume, no side-effect replay.
- `223.6/closure-regression.md`: backend runtime/node/event gates, runtime job
  gates, full frontend unit/rem gate, and diff check.
