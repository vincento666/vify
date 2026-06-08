# Tasks 039: Runtime Controlled Agent Fallback

## 039.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036-038.

## 039.1 Agent fallback port

- [ ] RED: unresolved runtime message cannot call fallback Agent.
- [ ] Add `FallbackAgentPort` and fake deterministic test implementation.
- [ ] Add `AGENT_FALLBACK` route action and payload formatter.
- [ ] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.1/`.
- [ ] Commit 039.1 only.

## 039.2 Agent output policy wrapper

- [ ] RED: Agent can propose unsupported side effects.
- [ ] Add schema validation for Agent outputs.
- [ ] Reject task mutation/start/suspend/resume/complete outputs.
- [ ] Require policy approval for handoff recommendation.
- [ ] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.2/`.
- [ ] Commit 039.2 only.

## 039.3 Clarification state and escalation

- [ ] RED: repeated clarification failure does not escalate.
- [ ] Track clarification attempts per runtime session/context.
- [ ] Route repeated failures to 033 `HANDOFF_TO_HUMAN`.
- [ ] Preserve active/suspended task state.
- [ ] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.3/`.
- [ ] Commit 039.3 only.

## 039.4 Agent fallback integration gate

- [ ] RED: E2E unresolved query lacks Agent fallback evidence.
- [ ] Prove Agent answer, Agent clarification, and Agent handoff
  recommendation flows.
- [ ] Prove FAQ/RAG/SOP gates still take precedence.
- [ ] Run full backend pytest or document unrelated failures.
- [ ] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/`.
- [ ] Commit 039.4 only.

## 039 Completion Gate

- [ ] Runtime-lab API E2E proves controlled Agent fallback behavior.
- [ ] Agent cannot mutate runtime task ledger in tests.
- [ ] 033 handoff escalation works through policy only.
