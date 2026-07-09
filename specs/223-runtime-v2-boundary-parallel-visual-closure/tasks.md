# Tasks — Spec 223

Evidence root:

```text
artifacts/slices/223-runtime-v2-boundary-parallel-visual-closure/<slice>/
```

## Slice 223.1 — Product Boundary Contract

- [x] Docs: update production runtime target with Workflow full DAG vs Chatflow
      conversational runtime boundary.
- [x] Docs: update DAG semantics with Chatflow controlled-DAG subset rules.
- [x] Docs: update node compatibility matrix to distinguish implementation
      support from UAT evidence.
- [x] Evidence: save doc diff summary under `223.1/docs-check.txt`.

## Slice 223.2 — Workflow True Parallel DAG Scheduler

- [x] RED: add slow three-branch `API_CALL` fan-out test proving serialized
      execution exceeds one-branch latency.
- [x] GREEN: execute eligible same-frontier `API_CALL` nodes concurrently.
- [x] Integration: prove API/LLM/Tool/Knowledge/Execute Workflow/Agent fan-out
      does not cross-contaminate outputs or scoped variables.
- [x] Contract: prove event sequences remain monotonic under concurrent branch
      completion.
- [x] Browser UAT: published Workflow run shows wall-clock and timeline overlap
      evidence.

## Slice 223.3 — Node Compatibility Evidence Matrix

- [x] RED: evidence matrix check fails when a first-class node lacks explicit
      Workflow/Chatflow evidence status.
- [x] GREEN: matrix records `covered`, `partial`, `automated-only`,
      `not-applicable`, or `missing`.
- [x] Contract: Chatflow and Workflow capability parity remains explicit and
      product differences are documented.
- [x] Docs: every partial/missing row links to an owning follow-up.

## Slice 223.4 — Workflow DAG Visual Evidence

- [x] RED: frontend test fails until selected/skipped edge states and join state
      are rendered.
- [x] GREEN: render fan-out, selected/skipped, join waiting/ready/completed, and
      parallel wave/timeline overlap.
- [x] Frontend rem: run `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`.
- [x] Browser UAT: save screenshots for a published Workflow parallel DAG run.

## Slice 223.5 — Chatflow Blocking/Resume Visual Evidence

- [x] RED: frontend test fails until the current blocking node has a waiting
      visual state.
- [x] GREEN: add looping border-light animation for the active
      `WAITING`/`INTERRUPTED` node.
- [x] Accessibility: support `prefers-reduced-motion` with a static waiting
      border.
- [x] Runtime UAT: prove resume returns to the same waiting node and does not
      replay completed side-effect nodes.
- [x] Browser UAT: save screenshots of waiting highlight, pending prompt, resume
      target, and post-resume completion.

## Slice 223.6 — Closure Regression

- [x] Unit / Integration / Contract: rerun Runtime V2 scheduler, node, job, and
      event gates affected by this spec.
- [x] Frontend unit / rem: full frontend unit and rem governance pass.
- [x] Browser UAT: Workflow full-DAG scenario and Chatflow blocking/resume
      scenario pass with saved screenshots.
- [x] Docs: update closure summary and link pass evidence.
