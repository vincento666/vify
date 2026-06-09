# Tasks 039: Runtime Controlled Agent Fallback

## 039.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036-038.

## 039.1 Agent fallback port

- [x] RED: unresolved runtime message cannot call fallback Agent.
- [x] Add `FallbackAgentPort` and fake deterministic test implementation.
- [x] Add `AGENT_FALLBACK` route action and payload formatter.
- [x] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.1/`.
- [x] Commit as part of 039 gated slice.

## 039.2 Agent output policy wrapper

- [x] RED: Agent can propose unsupported side effects.
- [x] Add schema validation for Agent outputs.
- [x] Reject task mutation/start/suspend/resume/complete outputs.
- [x] Require policy approval for handoff recommendation.
- [x] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.2/`.
- [x] Commit as part of 039 gated slice.

## 039.3 Clarification state and escalation

- [x] RED: repeated clarification failure does not escalate.
- [x] Track clarification attempts per runtime session/context.
- [x] Route repeated failures to 033 `HANDOFF_TO_HUMAN`.
- [x] Preserve active/suspended task state.
- [x] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.3/`.
- [x] Commit as part of 039 gated slice.

## 039.4 Agent fallback integration gate

- [x] RED: E2E unresolved query lacks Agent fallback evidence.
- [x] Prove Agent answer, Agent clarification, and Agent handoff
  recommendation flows.
- [x] Prove FAQ/RAG/SOP gates still take precedence.
- [x] Run full backend pytest or document unrelated failures.
- [x] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.4/`.
- [x] Commit as part of 039 gated slice.

## 039 Completion Gate

- [x] Runtime-lab API E2E proves controlled Agent fallback behavior.
- [x] Browser UAT proves controlled Agent answer and clarification-failure
  handoff.
- [x] Agent cannot mutate runtime task ledger in tests.
- [x] 033 handoff escalation works through policy only.

## 039.R1 Unified arbitration refactor

- [ ] RED: fallback Agent can still run as a separate post-gate answer layer.
- [ ] RED: unresolved user input lacks `AGENT_FALLBACK` candidate evidence.
- [ ] Add typed Agent fallback/clarify/handoff candidate generation or selected
  executor path.
- [ ] Ensure Agent execution happens only after central arbitration selects
  Agent fallback or no finite answer/task candidate survives recall.
- [ ] Preserve clarification counter and handoff escalation behavior.
- [ ] Save evidence under
  `artifacts/slices/039-runtime-controlled-agent-fallback/039.R1/`.
- [ ] Commit 039.R1 only.
