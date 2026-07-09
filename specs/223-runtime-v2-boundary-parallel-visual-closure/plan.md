# Plan — Spec 223

## Strategy

This is a correction and closure spec. Keep the historical completion records
intact, then add the missing contracts and evidence gates on top.

Implementation order:

1. Land the product boundary contract.
2. Correct the evidence wording around Runtime V2 DAG parallelism.
3. Add/repair tests that fail on serialized fan-out timing.
4. Implement true parallel execution only after the contract is frozen.
5. Add product-specific visual evidence:
   - Workflow: parallel DAG/wave/join visualization.
   - Chatflow: blocking node and resume visualization.
6. Run closure regression and record evidence.

## Workstream Ownership

- Runtime scheduler: Workflow true parallel execution and event ordering.
- Runtime node evidence: compatibility matrix and per-node UAT status.
- Workflow frontend: DAG selected/skipped/join/parallel wave visualization.
- Chatflow frontend: waiting node border-light animation and resume target.
- Runtime Ops: product-specific evidence views.

## Risks

### False Parallel Evidence

Prestarted `RUNNING` events can make a serialized wave look concurrent.

Mitigation:

- Pass criteria must include wall-clock timing and overlapping completion windows.
- Browser screenshots are supporting evidence, not the only proof.

### Chatflow Boundary Drift

Forcing Chatflow into a full DAG model could degrade the conversational resume
experience.

Mitigation:

- Chatflow visual language centers on waiting/resume, not parallel waves.
- Full DAG parallel claims stay Workflow-only unless a later spec explicitly
  promotes a Chatflow background-enrichment feature.

### Node Matrix Overclaim

Executor presence can be confused with full product evidence.

Mitigation:

- Add evidence status columns and force missing evidence to stay visible.

### Frontend Motion Accessibility

Looping border animation can distract or violate reduced-motion preference.

Mitigation:

- Implement `prefers-reduced-motion` fallback as part of the acceptance gate.

## Verification Layers

- Unit: scheduler, state projection, node evidence matrix, visual state helpers.
- Integration: true parallel slow-node fan-out, join, selected/skipped, resume.
- Contract: runtime refs, event ordering, compatibility evidence status.
- Frontend unit/rem: canvas and Runtime Ops visual states.
- Browser UAT: published Workflow DAG and Chatflow waiting/resume scenarios.

## Exit Criteria

- Spec 223 tasks are all complete.
- Gap evidence from run `28799`/`28800` is superseded by pass evidence showing
  true parallel Workflow execution.
- Chatflow has explicit waiting/resume visual evidence.
- Documentation no longer implies Chatflow full-DAG parity or parallel pass
  status without evidence.
