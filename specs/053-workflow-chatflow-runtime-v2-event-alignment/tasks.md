# Tasks 053: Workflow/Chatflow Runtime V2 Event Alignment

## 053.0 Spec Sign-off

- [x] Confirm 053 is evaluation/design-first unless explicitly promoted to
      implementation.
- [x] Confirm target direction is async run lifecycle, not only streaming POST.
- [x] Confirm existing Workflow/Chatflow APIs remain compatible.
- [x] Confirm customer-assistant runtime, eventful sub-agent calling, and
      L1/L2 event semantics are stable enough to use as reference models.
- [x] Confirm worker async run semantics are not a blocker for 053 design, and
      that hard timeout/cancellation/worker refs are delegated to 056.
- [x] Save Browser UAT readiness evidence under
      `artifacts/slices/053-workflow-chatflow-runtime-v2-event-alignment/053.0/`.

## 053.1 Current Runtime Audit

- [x] Document current Workflow/Chatflow run/session/event/checkpoint behavior.
- [x] Identify sync-vs-streaming gaps.

## 053.2 Event Vocabulary Alignment

- [x] Map Workflow/Chatflow node events to L1/L2 event levels.
- [x] Align payload fields with customer-assistant events.

## 053.3 Async Run Lifecycle Proposal

- [x] Propose API routes and persistence changes.
- [x] Define compatibility wrapper behavior.
- [x] Map old Chatflow/SOP worker invocation onto the proposed run/status/event
      result calling convention.

## 053.4 Spike Decision

- [x] Decide whether to implement a narrow spike.
- [x] If approved, assign the first executable slice to 058 or later.
- [x] Do not implement the spike in 053.
- [x] Recommended follow-on sequence is 054 synthetic eval, 055 LLM primary
      path, 056 worker runtime hardening, 057 operator turn mode, and 058
      realtime transport/Workflow-Chatflow v2 spike.

## Evidence

- 053.1-053.4 audit report:
  `artifacts/slices/053-workflow-chatflow-runtime-v2-event-alignment/053.1/runtime-v2-audit.md`
