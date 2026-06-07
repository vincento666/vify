# Tasks 033: Runtime Fallback Policy

## 033.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 032 gates.
- [x] Keep fallback systems under runtime policy gate control.
- [x] Commit 030-033 spec skeleton documents only.

## 033.1 FAQ answer gate

- [ ] Blocked until 032 completion gate passes.
- [ ] RED: FAQ policy tests fail for exact match, semantic match, active-SOP
  safe answer, active-SOP ambiguity, and confidence margin behavior.
- [ ] Implement FAQ exact/high-confidence answer gate.
- [ ] Preserve active SOP task state for FAQ answers.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.1/`.
- [ ] Gates pass.
- [ ] Commit 033.1 only.

## 033.2 RAG answer gate

- [ ] RED: RAG policy tests fail for evidence, low-confidence clarify, and no
  SOP mutation behavior.
- [ ] Add RAG answer route action and evidence payload.
- [ ] Ensure RAG document snippets are not SOP classifier targets.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.2/`.
- [ ] Gates pass.
- [ ] Commit 033.2 only.

## 033.3 Controlled Agent fallback

- [ ] RED: Agent fallback tests fail for allowed answer actions, prohibited
  task-ledger mutation, clarification proposal, and handoff recommendation.
- [ ] Add fallback Agent port.
- [ ] Add policy wrapper around Agent outputs.
- [ ] Ensure Agent cannot directly start, suspend, resume, complete, or handoff
  a task.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.3/`.
- [ ] Gates pass.
- [ ] Commit 033.3 only.

## 033.4 Human handoff policy

- [ ] RED: handoff policy tests fail for explicit request, compliance trigger,
  repeated clarification failure, Agent recommendation approval, and unsupported
  process.
- [ ] Add handoff route action and runtime events.
- [ ] Preserve active/suspended task summaries for handoff context.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.4/`.
- [ ] Gates pass.
- [ ] Commit 033.4 only.

## 033.5 End-to-end fallback policy gate

- [ ] RED: E2E tests fail for FAQ-before-SOP safe answer, active-SOP ambiguity
  clarification, RAG fallback, Agent clarification, and human handoff.
- [ ] Expose fallback decision evidence in runtime-lab API.
- [ ] Run targeted runtime-lab and Chatflow adapter tests.
- [ ] Run full backend pytest or document unrelated failures.
- [ ] Run browser UAT only if frontend is changed.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.5/`.
- [ ] Gates pass.
- [ ] Commit 033.5 only.
