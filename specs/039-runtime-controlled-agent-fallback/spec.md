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

## Specification Sign-off

Status: ready for implementation.

Numbering was rechecked on 2026-06-09. 039 follows 038 and is limited to a
policy-controlled fallback Agent. It must not grant the Agent direct authority
over SOP task mutation.
