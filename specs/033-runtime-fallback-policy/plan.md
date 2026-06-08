# Plan 033: Runtime Handoff Foundation

## Role

033 builds the shared handoff/fallback control-plane primitive for runtime-lab.
It is the first layer after 034 and before FAQ/RAG/Agent fallback routing.

Later specs may decide to answer, clarify, use RAG, or invoke a fallback Agent,
but every layer must use the same `HANDOFF_TO_HUMAN` route action when it needs
human escalation.

## Architecture

```text
RuntimeLabService.handle_message
  -> ExplicitHandoffSignalDetector
  -> candidate recall
  -> PolicyGate
  -> HandoffRuntimeAdapter
  -> HandoffService / runtime events
```

033 keeps task ownership unchanged:

- runtime-lab owns route decision and active/suspended task ledger;
- existing handoff module owns human ticket lifecycle;
- Chatflow still owns internal SOP execution state;
- future FAQ/RAG/Agent gates can only request handoff through policy.

## Route Contract

Add:

```text
RouteDecision.action = HANDOFF_TO_HUMAN
CandidateType.HANDOFF_TO_HUMAN
Classifier allowed action HANDOFF_TO_HUMAN
Runtime event HANDOFF_REQUESTED
Runtime event HANDOFF_DECIDED
```

Decision evidence must include:

- `sourceLayer`: `explicit_signal`, `faq_policy`, `rag_policy`,
  `agent_policy`, `clarification_policy`, or `system_policy`;
- `reasonCode`: stable code such as `USER_REQUEST`, `COMPLAINT`,
  `COMPLIANCE`, `SAFETY`, `UNSUPPORTED`, `REPEATED_CLARIFY_FAILURE`;
- `matchedTerms`;
- active/suspended task summaries;
- recent transcript summary when available.

## Explicit Trigger Groups

Initial hard-stop templates:

- human support: `转人工`, `人工客服`, `找人工`, `人工处理`;
- complaint/escalation: `投诉`, `主管`, `升级处理`, `不满意`;
- compliance/safety: `监管`, `民航局`, `报警`, `安全事故`;
- unsupported: `这个机器人处理不了`, `无法办理`, `不要机器人`.

These templates should be configurable data in runtime-lab domain code first.
Do not put them in frontend-only logic.

## TDD Strategy

RED first:

- classifier rejects `HANDOFF_TO_HUMAN` before action support exists;
- explicit trigger tests fail before detector support exists;
- service integration fails before runtime event/context snapshot is emitted;
- contract/E2E fails before API response includes normalized handoff evidence.

GREEN:

- minimal action/candidate support;
- minimal explicit detector;
- minimal handoff adapter over existing handoff service or fake adapter in
  tests;
- no frontend change unless 040 later promotes UI evidence.

## SDD Gates

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and evidence under:

```text
artifacts/slices/033-runtime-fallback-policy/
  033.1/
  033.2/
  033.3/
  033.4/
```

Do not start FAQ/RAG/Agent specs until 033 action/event/context contracts pass.

## Non-Goals

- no FAQ/RAG answer policy;
- no fallback Agent implementation;
- no human-agent console;
- no frontend routing page changes;
- no autonomous state mutation outside runtime-lab policy.

## Completion Notes

Implemented:

- `HANDOFF_TO_HUMAN` candidate/action support in the finite routing contract.
- Explicit handoff trigger groups for human support, complaint, compliance,
  safety, and unsupported-process wording.
- Runtime handoff branch that emits `HANDOFF_DECIDED` and
  `HANDOFF_REQUESTED`, builds a context snapshot, optionally calls a one-way
  handoff service port, and preserves active/suspended task state.
- API contract evidence that `/api/v1/runtime-lab/sessions/{id}/messages`
  returns handoff route evidence and does not advance the active SOP.

Evidence is saved under
`artifacts/slices/033-runtime-fallback-policy/033.1/` through `033.4/`.

Final 033 gates:

- targeted runtime-lab unit/integration/contract: `033.4/final-targeted.txt`
  (`54 passed`);
- e2e runtime-lab API regression: `033.4/e2e.txt` (`4 passed`);
- browser-control UAT: `033.4/uat.md`,
  `033.4/browser-uat-result.json`, and
  `033.4/screenshots/browser-uat-handoff.png` (`passed=true`);
- full backend run: attempted and stopped at external live provider acceptance,
  documented in `033.4/full-backend-note.md`.
