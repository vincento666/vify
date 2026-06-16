# 074 Customer Service Workbench Loop Productization

## Goal

Turn the customer-assistant panel into a repeatable seated-agent demo workbench.
The workbench must open seeded demo stories, show multi-customer session context,
task ledger state, blocking waits, proposed actions, and event evidence, then
support the human confirmation and recovery controls needed by the MVP story.

## Acceptance Criteria

- The workbench can discover and load 073 seeded demo stories without the user
  manually typing session IDs.
- Loading a story refreshes session, tasks, events, and proposed actions from the
  backend and renders them in the existing lanes/panels.
- Seeded stories demonstrate:
  - parallel refund + baggage tasks;
  - invoice task interrupted by flight-status inquiry;
  - Chatflow wait/resume recommendation path.
- Proposed actions remain gated by human confirm/reject/execute controls and
  write updated status back through API calls.
- Retry/cancel/resume task controls are visible when task state permits, and
  each control writes an audit/event trail.
- The operator can ask internal questions against the loaded customer context,
  task ledger, and knowledge bindings.
- Browser UAT proves the loaded demo story has no horizontal overflow and that
  the customer lane stays free of internal-only controls.

## Slices

### 074.1 Seeded Story Picker And Load Path

Expose a backend demo-story listing endpoint and a frontend story selector that
loads the seeded session ledger into the workbench.

### 074.2 Human Task Control Loop

Add explicit retry/cancel/resume affordances for task rows, implemented through
proposed task-control actions and refreshed ledger state.

### 074.3 Knowledge-Backed Operator Advisory

Bind operator-side questions to session context, task ledger, and seeded
knowledge/advisory material.

## Evidence

- RED / unit / integration / frontend / browser evidence lives under
  `artifacts/slices/074-customer-service-workbench-loop-productization/<slice>/`.

## Non-goals

- 075 owns configurable worker/skill catalog productization.
- 077 owns verified host auth, tenant isolation, and broad redaction gates.
- 078 owns the final end-to-end demo story package after 074-077 are complete.
