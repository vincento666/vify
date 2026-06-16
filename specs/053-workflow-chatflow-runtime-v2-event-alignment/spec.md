# Spec 053: Workflow/Chatflow Runtime V2 Event Alignment

## Goal

Evaluate and design a Workflow/Chatflow runtime v2 that aligns node-level
execution events with the customer-assistant/React-worker event model.

053 is the bridge from customer-assistant runtime events back into the general
canvas runtimes. In this phase it is design/audit only. It should not replace
the existing synchronous Workflow/Chatflow APIs or introduce a runtime v2
implementation.

## Dependency

053 depends on:

- 048 customer-assistant L1 event stream;
- 049 React worker L2 event vocabulary;
- 052 eventful customer-assistant sub-agent contract;
- a stable customer-assistant runtime using the legacy Chatflow/SOP worker
  successfully in MVP flows;
- a stable enough sub-agent/worker async run shape: run id, status, events,
  result, and cancellation/resume semantics where supported;
- current Hify Workflow/Chatflow run/checkpoint/session model.

## Timing

053 may start as an audit/design spec once 047-052 pass code gates and Browser
UAT. Implementation should remain gated until the missing worker runtime
semantics are explicitly assigned to follow-on specs.

If worker async run semantics are not stable when 053 is reached, 053 should
record that gap and defer hard timeout/cancellation/worker refs to Spec 056
instead of attempting Workflow/Chatflow runtime v2 implementation immediately.

## Background

Current Hify Chatflow/Workflow execution is a synchronous persisted run model.
Some endpoints can return stored or computed stream-like payloads, but the core
run lifecycle is not a background async run with a durable event stream.

The target direction for Hify is an async run lifecycle:

```text
POST /runs -> runId
GET /runs/{runId}
GET /runs/{runId}/events/stream
POST /runs/{runId}/cancel
POST /runs/{runId}/resume
```

Single-connection streaming POST can remain useful for debug preview, but it
should not become the long-term primary product/runtime contract.

## MVP Scope Guard

053 is an audit and alignment MVP. Its output is an implementation proposal,
compatibility plan, and go/no-go decision for later runtime v2 work. It must
not replace the existing Workflow/Chatflow APIs wholesale, move the customer
assistant back onto the canvas runtime, or block the customer-assistant product
loop while pursuing a bottom-layer unification.

Any executable Workflow/Chatflow v2 spike belongs to Spec 058 after the worker
runtime hardening and data readiness questions are settled.

## Event Alignment

Align Workflow/Chatflow node events with the same layering:

L1:

```text
workflow_run_started
workflow_node_started
workflow_node_completed
workflow_node_failed
workflow_run_completed
workflow_run_failed
```

L2:

```text
llm_call_started
llm_call_completed
tool_call_started
tool_call_completed
chatflow_checkpointed
chatflow_interrupted
variable_collected
```

The mapping should let customer-assistant workers summarize internal
Chatflow/SOP progress without hardcoding each node type into the operator UI.

## Acceptance Criteria

- Document current Hify Workflow/Chatflow runtime behavior and gaps.
- Define runtime v2 event envelope aligned with customer-assistant events.
- Define async run lifecycle API proposal and compatibility strategy.
- Decide whether the current product gates allow starting 053 design work.
- Decide which implementation spec owns the first narrow run/event spike.
- Do not break existing Workflow/Chatflow API consumers.
