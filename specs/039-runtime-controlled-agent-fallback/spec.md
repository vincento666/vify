# Spec 039: Runtime Controlled Agent Fallback

## Goal

Add a controlled fallback Agent layer for unresolved or long-tail conversations
after FAQ, SOP, and RAG gates have failed or asked for escalation.

The fallback Agent may reason and use knowledge, but it must not mutate SOP
state or directly execute handoff. Runtime policy remains the final authority.

## Dependency

Required:

- 033 handoff foundation complete;
- 036 FAQ exact gate complete;
- 037 FAQ embedding gate complete;
- 038 RAG answer gate complete.

## Scope

In scope:

- `AGENT_FALLBACK` route action;
- `ASK_CLARIFICATION` normalized action if separated from legacy `CLARIFY`;
- fallback Agent port with deterministic fake implementation for tests;
- policy wrapper for Agent outputs:
  - answer;
  - ask clarification;
  - summarize user demand;
  - recommend handoff;
- clarification failure counter and handoff escalation through 033;
- proof Agent cannot start/suspend/resume/complete SOP tasks.

Out of scope:

- autonomous tool calling that changes business records;
- full human-agent console;
- unrestricted open-ended Agent control over runtime ledger.

## Routing Position

```text
033 handoff hard stops
  -> FAQ
  -> SOP/resume
  -> RAG
  -> 039 controlled Agent fallback
  -> 033 HANDOFF_TO_HUMAN if policy approves
```

## Acceptance Criteria

- unresolved query reaches fallback Agent only after earlier gates decline;
- Agent answer returns `AGENT_FALLBACK` with policy evidence;
- Agent clarification returns `ASK_CLARIFICATION`/`CLARIFY` and increments
  clarification state;
- repeated clarification failure triggers `HANDOFF_TO_HUMAN`;
- Agent handoff recommendation is not final until policy approves;
- Agent cannot mutate runtime task ledger.

## Completion Capability

After 039, runtime-lab has a safe bottom layer for long-tail support: it can
answer, clarify, calm, summarize, or recommend handoff without breaking SOP
state discipline.

## Completion Evidence

Status: completed on 2026-06-09.

Numbering was rechecked on 2026-06-09. 039 follows 038 and is limited to a
policy-controlled fallback Agent. It must not grant the Agent direct authority
over SOP task mutation.

Evidence:

- RED:
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.1/red.txt`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.2/red.txt`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/red.txt`
- Unit/integration:
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.1/unit.txt`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.2/unit-integration.txt`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.3/unit-integration.txt`
- API E2E/regression:
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/e2e.txt`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/final-targeted.txt`
  - Result: `47 passed, 1 warning`
- Browser UAT:
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/browser-uat-result.json`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/uat.md`
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/screenshots/browser-uat-agent.png`
- Full backend:
  - `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/full-backend.txt`
  - Result: `472 passed, 8 skipped, 15 failed`; failures match existing
    unrelated runtime-lab scale/workflow baseline issues and are documented in
    the artifact.
