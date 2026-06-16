# Plan 034: Unified Routing Chat Lab

## Architecture

```text
Composer menu
  -> /runtime-lab/chat
  -> UnifiedRoutingChatLab.vue
  -> runtimeLab API client
  -> /api/v1/runtime-lab/sessions
  -> /api/v1/runtime-lab/sessions/{id}/messages
  -> /api/v1/runtime-lab/sessions/{id}/tasks
  -> /api/v1/runtime-lab/sessions/{id}/events
```

The page is a frontend-only lab shell over the already implemented backend
control plane. It intentionally keeps a one-way dependency:

```text
frontend lab -> runtime-lab API -> runtime-lab service -> Chatflow adapter
```

The existing ordinary Chat system remains reachable through `/chat` for
comparison. 034 does not attempt to multiplex Agent chat and runtime-lab turns
inside one backend endpoint.

## TDD Strategy

RED tests first:

- route exists at `/runtime-lab/chat`;
- composer navigation includes the lab entry;
- scenario presets expose all five airline SOPs and correct start messages;
- runtime-lab API client calls the expected endpoints;
- transcript helpers summarize runtime turns without duplicating backend
  routing logic.

Implementation then adds the smallest Vue page that satisfies the tests and is
usable in a browser UAT.

## UI Shape

Use a quiet operational layout:

- left column: system comparison, session controls, SOP switch panel;
- center column: transcript and message composer;
- right column: route decision, active/suspended task ledger, recent events.

The SOP switch panel is a tester affordance. Normal user turns still go through
the text composer and backend route arbitration.

## Evidence Plan

Use:

```text
artifacts/slices/034-unified-routing-chat-lab/
  034.0/
  034.1/
  034.2/
```

Evidence:

- RED frontend test output;
- targeted frontend unit output;
- REM governance output;
- targeted backend airline gate output;
- browser UAT markdown plus screenshot.

## Risks

- Existing frontend files are dirty in the working tree. Stage only 034-related
  changes.
- Current runtime-lab live LLM acceptance remains opt-in; browser UAT may use
  deterministic configured test SOP responses unless live credentials are
  explicitly provided.
- The existing ordinary Chat page requires Agent/session setup. 034 exposes it
  as a comparison entry rather than forcing it into the runtime-lab lab flow.

## 034.6 Expansion Strategy

Strong triggers are treated as configurable templates on SOP manifests:

- phrase templates cover exact operational labels and high-value synonyms;
- all-term templates cover natural utterances where the important words are not
  adjacent;
- regex templates cover compact phrase families when literal keyword lists
  would be brittle;
- score tuning resolves high-risk overlaps such as group booking vs ordinary
  booking, flight status vs irregular flight, and membership vs ancillary
  products.

The default classifier remains fake/deterministic for repeatable gates. A real
LLM arbitrator can be injected through the constrained classifier adapter, and
the route evidence must show whether the turn used `fake` or `llm` mode.

## 034.13 Promotion Plan

034.13 turns the successful airline SOP test corpus into a local development
configuration that testers can inspect and use directly:

- seed the 15 airline SOPs as published Chatflow workflows in the current
  development database;
- write only non-secret RuntimeLab binding/model settings into local `.env`;
- keep provider API keys in process environment or provider config, never in
  frontend payloads or committed files;
- expose `/api/v1/runtime-lab/config` for frontend display of Chatflow IDs,
  binding existence, arbitrator mode, and model;
- render the config in the runtime-lab page alongside the existing intent scope
  controls;
- prove with browser UAT that the displayed bindings are not decorative by
  completing a multi-SOP start/switch/resume path through the visible page.

## 034.17 Inspector Plan

034.17 promotes the runtime-lab page from a route transcript viewer to a
Chatflow-bound debugging surface:

- the frontend still does not author system configuration directly; it reads
  `/api/v1/runtime-lab/config` and lets testers choose the current experiment
  scope from the actually bound Chatflow SOPs;
- configuration adjustment for the underlying SOP remains in the existing
  Chatflow canvas, opened through each binding's `canvasPath`;
- the right inspector reads
  `/api/v1/runtime-lab/sessions/{session_id}/chatflow-trace`, which is derived
  from RuntimeLab checkpoints, Chatflow session state, Chatflow events, and
  workflow node run rows;
- the trace panel is designed as the future anchor for FAQ/RAG/embedding
  routing: explicit match, semantic recall, LLM arbitration, clarification,
  FAQ/RAG fallback, and handoff can be added as neighboring lanes without
  changing the center conversation flow.
