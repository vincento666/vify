# 032.4 E2E Gate Plan

## Status

Pre-implementation sign-off only. No E2E tests have been written in this gate.

032.4 starts only after 032.3 adapter implementation gates pass.

## Required E2E Path

The runtime-lab API must prove a real Chatflow-backed SOP path:

```text
create runtime session
  -> start real Chatflow SOP
  -> reach waiting checkpoint
  -> switch to another mock or real SOP if required by the path
  -> resume real Chatflow SOP from checkpoint
  -> complete confirmation
  -> verify runtime ledger state and Chatflow state
```

The exact path may be narrowed if 032.3 proves only one real Chatflow-backed SOP
is configured, but it must still cover start, continue, suspend, resume, and
complete.

## Regression Gates

Run and save evidence for:

- targeted runtime-lab tests;
- targeted Chatflow run/resume/session-state tests;
- dependency-direction gate;
- full backend pytest or documented unrelated failures.

## Non-Goals

Do not:

- add frontend UAT unless frontend changes are introduced;
- connect multiple real SOPs;
- implement fallback FAQ/RAG/Agent/handoff policy.
