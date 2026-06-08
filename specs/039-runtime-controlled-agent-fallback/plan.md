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

Completed evidence:

- `039.1/red.txt`, `039.1/unit.txt`
- `039.2/red.txt`, `039.2/unit-integration.txt`
- `039.3/unit-integration.txt`
- `039.4/red.txt`, `039.4/e2e.txt`
- `039.4/final-targeted.txt`: `47 passed, 1 warning`
- `039.4/browser-uat-result.json`: Swagger Browser UAT PASS
- `039.4/screenshots/browser-uat-agent.png`
- `039.4/full-backend.txt`: `472 passed, 8 skipped, 15 failed`

## SDD Gate

039 started only after 033, 036, 037, and 038 route contracts passed. It
remains a policy-controlled fallback layer and does not give the Agent direct
authority to start, suspend, resume, complete, or hand off SOP tasks.

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and the corresponding
artifact directory before sign-off. 039 is complete because Agent output is
schema-validated, unsafe side effects are rejected, clarification counters are
tested, and final handoff still goes through the 033 control-plane action.
