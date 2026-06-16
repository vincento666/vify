# Plan 053: Workflow/Chatflow Runtime V2 Event Alignment

## Architecture Questions

053 should answer:

- Which existing run/session/checkpoint tables can be reused?
- Does Workflow and Chatflow share one run lifecycle or keep separate facades?
- How are node events persisted and streamed?
- How does resume/cancel interact with existing checkpoint behavior?
- Which old synchronous endpoints stay as compatibility wrappers?
- Which customer-assistant sub-agent/worker async run concepts become the
  shared calling convention?

## Entry Criteria

Start 053 audit/design only after these are true:

- customer-assistant runtime MVP is stable with old Chatflow/SOP worker calls;
- 048 live L1 events are stable in the operator panel;
- 049 restricted React worker events are stable enough to define L2 vocabulary;
- 052 eventful `spawn_sub_agent` returns durable run/status/event/result refs;
- frontend build, backend tests, frontend tests, and Browser UAT have passed.

Do not start 053 implementation until worker async run semantics are stable
enough to compare against Workflow/Chatflow node execution. If that item is
missing, implement Spec 056 first.

## Investigation Plan

Compare:

- current Hify Workflow/Chatflow implementation;
- customer-assistant 048 event ledger;
- React worker L2 events from 049;
- single-connection streaming POST designs as a debug-preview option.

## Output

053 produces ADR/spec output only. If implementation is approved, it must be
scheduled into a later spec, starting with one narrow vertical slice rather than
a full runtime replacement.

Recommended follow-on sequence:

```text
054 Synthetic Eval And LLM Promotion Readiness
055 LLM Primary Path MVP
056 Worker Runtime Hardening
057 Operator Turn Mode
058 Realtime Transport And Workflow/Chatflow V2 Spike
```
