# Tasks 032: Chatflow SOP Integration

## 032.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 031 gates.
- [x] Limit integration to one real Chatflow-backed SOP path.
- [x] Commit 030-033 spec skeleton documents only.

## 032.1 Chatflow boundary discovery

- [ ] Blocked until 031 completion gate passes.
- [ ] Inspect current Chatflow run/resume/session-state APIs.
- [ ] Document the chosen adapter call path.
- [ ] Document any 031 contract gaps before implementation.
- [ ] Save evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.1/`.
- [ ] Commit 032.1 only.

## 032.2 Real adapter RED tests

- [ ] RED: real adapter tests fail for start, continue, suspend checkpoint,
  resume, and complete.
- [ ] Add one test-only Chatflow SOP fixture if no suitable fixture exists.
- [ ] Save RED evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.2/`.
- [ ] Commit 032.2 red tests only if repository convention allows, otherwise
  continue to 032.3 before commit.

## 032.3 Real adapter implementation

- [ ] Implement `ChatflowSopRuntimeAdapter`.
- [ ] Map runtime request DTOs to Chatflow service inputs.
- [ ] Map Chatflow outputs to runtime result DTOs.
- [ ] Preserve checkpoint serialization.
- [ ] Save evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.3/`.
- [ ] Gates pass.
- [ ] Commit 032.3 only.

## 032.4 Runtime E2E with real Chatflow SOP

- [ ] RED: API E2E fails for real Chatflow-backed SOP start, suspend, resume,
  and complete.
- [ ] Add runtime-lab API E2E for the real adapter path.
- [ ] Prove mock SOP path still works.
- [ ] Run targeted Chatflow tests.
- [ ] Run full backend pytest or document unrelated failures.
- [ ] Save evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.4/`.
- [ ] Gates pass.
- [ ] Commit 032.4 only.

## Future specs, not 032 tasks

- [ ] FAQ/RAG answer routing.
- [ ] Knowledge/Clarification Agent fallback.
- [ ] Human handoff policy.
