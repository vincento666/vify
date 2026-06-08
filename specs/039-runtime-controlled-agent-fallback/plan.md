# Plan 039: Runtime Controlled Agent Fallback

## Architecture

```text
RuntimeLabService
  -> FAQ/SOP/RAG layers
  -> FallbackAgentPort
  -> AgentOutputPolicy
  -> route action AGENT_FALLBACK | CLARIFY | HANDOFF_TO_HUMAN
```

Agent output schema:

```text
{
  responseType: answer | clarification | handoff_recommendation,
  answer,
  clarificationQuestion,
  handoffReason,
  confidence,
  citations,
  safetyFlags
}
```

Policy output:

- allowed: answer text, clarification text, handoff recommendation;
- forbidden: task mutation, direct handoff ticket creation, SOP action
  selection, fabricated business status.

## TDD Strategy

RED tests:

- fallback Agent port absent;
- unresolved query does not reach Agent after earlier gates decline;
- Agent recommendation can bypass policy;
- repeated clarification failure does not escalate;
- Agent can mutate task ledger.

GREEN:

- add fake Agent port;
- add policy wrapper and response validation;
- add clarification state/counter;
- route approved handoff through 033 only.

## Evidence

Use:

```text
artifacts/slices/039-runtime-controlled-agent-fallback/
  039.1/
  039.2/
  039.3/
  039.4/
```

Live Agent/LLM behavior remains opt-in; CI uses fake deterministic Agent.

## SDD Gate

039 may start only after 033, 036, 037, and 038 route contracts pass. It must
remain a policy-controlled fallback layer and must not give the Agent direct
authority to start, suspend, resume, complete, or hand off SOP tasks.

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and the corresponding
artifact directory before sign-off. 039 is complete only when Agent output is
schema-validated, unsafe side effects are rejected, clarification counters are
tested, and final handoff still goes through the 033 control-plane action.
