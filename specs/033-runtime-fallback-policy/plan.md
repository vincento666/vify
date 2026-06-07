# Plan 033: Runtime Fallback Policy

## Architecture

Add fallback policy as route actions controlled by the runtime policy gate.

Suggested conceptual components:

```text
FaqAnswerGate
RagAnswerGate
FallbackAgentPort
HandoffPolicy
RuntimePolicyGate
```

The exact files should follow the runtime module shape after 032.

## Control Plane Rule

The route control plane owns final decisions.

FAQ, RAG, and Agent systems provide evidence and proposed responses. They do not
own runtime task mutation.

## Active SOP Safety

Every fallback path must state whether it mutates SOP state.

Expected defaults:

- `ANSWER_FAQ`: no SOP mutation;
- `ANSWER_RAG`: no SOP mutation;
- `ASK_CLARIFICATION`: no SOP mutation;
- `AGENT_FALLBACK`: no SOP mutation unless a future explicit tool policy says
  otherwise;
- `HANDOFF_TO_HUMAN`: emits handoff event and may pause task according to
  explicit policy.

## Test Strategy

Unit tests:

- FAQ confidence and margin policy;
- RAG confidence and evidence policy;
- Agent fallback allowed/prohibited actions;
- handoff trigger rules.

Integration tests:

- active SOP plus safe FAQ answer;
- active SOP plus ambiguous question asks clarification;
- no-active long-tail query reaches RAG or Agent;
- repeated clarification failure triggers handoff;
- Agent recommendation requires policy approval before handoff.

Contract/E2E tests:

- runtime-lab API exposes fallback decision evidence;
- existing SOP routing and real Chatflow adapter path remain valid.

## Evidence

Use:

```text
artifacts/slices/033-runtime-fallback-policy/
  033.0/
  033.1/
  ...
```

Frontend/browser UAT is required only if 033 changes user-visible UI.

## Non-Goals

Do not:

- give Agent autonomous control over SOP task state;
- merge fallback Agent with intent classifier;
- remove constrained SOP arbitration;
- build a full human-service console in this spec.
