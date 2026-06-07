# Spec 033: Runtime Fallback Policy

## Goal

Add controlled FAQ, RAG, Knowledge/Clarification Agent, and human handoff
fallback policy to the runtime routing control plane after real Chatflow SOP
integration is proven.

033 is about response/fallback policy, not SOP execution mechanics.

## Dependency

033 starts only after 032 gates pass.

Required 032 capabilities:

- one real Chatflow-backed SOP path;
- stable adapter integration;
- preserved task ledger and checkpoint behavior;
- existing Chatflow regression gates passing.

## Scope

In scope:

- policy actions:
  - `ANSWER_FAQ`;
  - `ANSWER_RAG`;
  - `ASK_CLARIFICATION`;
  - `AGENT_FALLBACK`;
  - `HANDOFF_TO_HUMAN`;
- FAQ exact and semantic answer routing;
- RAG retrieval evidence for fallback answer generation;
- controlled Knowledge/Clarification Agent fallback;
- handoff trigger policy;
- active-SOP safe handling of FAQ and fallback answers;
- route evidence explaining why SOP state did or did not mutate.

Out of scope:

- frontend agent console;
- full human-agent chat UI;
- production analytics dashboards;
- broad knowledge-base refactor;
- unconstrained autonomous Agent control over SOP state.

## Policy Design

033 keeps the route control plane in charge.

```text
Safety and handoff hard stops
  -> FAQ exact/high confidence answer gate
  -> SOP/resume candidate recall and arbitration
  -> FAQ/RAG semantic answer gate
  -> controlled Agent fallback
  -> human handoff
```

Active SOP behavior is stricter:

- FAQ answers can be returned without mutating active SOP state when the user is
  clearly asking a question;
- uncertain "question vs business handling" cases must clarify instead of
  collecting SOP slots;
- Agent fallback cannot start, suspend, resume, or complete SOP tasks directly;
- handoff policy can pause or mark task state according to an explicit runtime
  event.

## FAQ Policy

FAQ matching methods may include:

- exact question match;
- normalized keyword/alias match;
- BM25/ES lexical recall if available;
- vector recall if available;
- rerank if available;
- confidence and margin policy.

High-confidence FAQ answers may exit before SOP arbitration only when policy
rules say the answer is safe. In active-SOP contexts, the response must preserve
task state unless an explicit route decision says otherwise.

## RAG Policy

RAG retrieval is for long-tail answer generation and evidence-backed responses.
RAG document snippets are not SOP targets.

The RAG answer path must return:

- cited source metadata when available;
- retrieval confidence or score evidence;
- generated answer;
- safety result;
- decision reason.

## Agent Fallback Policy

The fallback Agent may:

- dynamically search knowledge;
- answer long-tail questions;
- provide calming or service-oriented small talk;
- summarize user demand;
- ask clarification questions;
- recommend human handoff.

The fallback Agent must not:

- mutate runtime task ledger directly;
- decide final handoff without policy gate approval;
- bypass SOP safety rules;
- fabricate unavailable business status.

## Handoff Policy

Handoff triggers may include:

- explicit user request for human support;
- safety or compliance trigger;
- repeated clarification failure;
- repeated low-confidence routing;
- Agent fallback recommendation approved by policy;
- unsupported business process.

Handoff emits explicit runtime events and preserves enough state for the human
agent to understand active and suspended tasks.

## Acceptance Criteria

- High-confidence FAQ can answer before SOP arbitration when safe.
- Active SOP question can be answered without consuming the message as a slot.
- Ambiguous active SOP question vs handling request asks clarification.
- RAG fallback returns evidence and does not mutate SOP state.
- Agent fallback is controlled by policy and cannot mutate ledger directly.
- Handoff is triggered by explicit policy and emits audit events.
- Existing 030 routing and 032 Chatflow-backed SOP paths still pass.

## Completion Gate

033 is complete only when:

- FAQ/RAG/Agent/handoff policy tests pass;
- active-SOP safety cases pass;
- handoff event and state tests pass;
- full backend pytest passes or unrelated failures are documented;
- browser UAT is executed if any user-visible frontend behavior is changed;
- evidence is saved under `artifacts/slices/033-runtime-fallback-policy/`;
- one git commit contains only 033 changes.
