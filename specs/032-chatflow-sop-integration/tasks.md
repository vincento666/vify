# Tasks 032: Chatflow SOP Integration

## 032.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 031 gates.
- [x] Limit integration to one real Chatflow-backed SOP path.
- [x] Commit 030-033 spec skeleton documents only.
- [x] Add 032.0 spec sign-off.
- [x] Save documentation-only evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.0/`.
- [x] Confirm no application code, tests, API behavior, or schema changes are
  included in 032.0.

## 032.1 Chatflow boundary discovery

- [x] Blocked until 031 completion gate passes.
- [x] Inspect current Chatflow run/resume/session-state APIs.
- [x] Document the chosen adapter call path.
- [x] Document any 031 contract gaps before implementation.
- [x] Save evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.1/`.
- [x] Commit 032 documentation sign-off only.

## 032.2 Real adapter RED tests

- [x] Document pre-implementation RED-test sign-off under
  `artifacts/slices/032-chatflow-sop-integration/032.2/`.
- [ ] RED: real adapter tests fail for start, continue, suspend checkpoint,
  resume, and complete.
- [ ] Add one test-only Chatflow SOP fixture if no suitable fixture exists.
- [ ] Save RED evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.2/`.
- [ ] Commit 032.2 red tests only if repository convention allows, otherwise
  continue to 032.3 before commit.

## 032.3 Real adapter implementation

- [x] Document pre-implementation adapter mapping sign-off under
  `artifacts/slices/032-chatflow-sop-integration/032.3/`.
- [ ] Implement `ChatflowSopRuntimeAdapter`.
- [ ] Map runtime request DTOs to Chatflow service inputs.
- [ ] Map Chatflow outputs to runtime result DTOs.
- [ ] Preserve checkpoint serialization.
- [ ] Save evidence under
  `artifacts/slices/032-chatflow-sop-integration/032.3/`.
- [ ] Gates pass.
- [ ] Commit 032.3 only.

## 032.4 Runtime E2E with real Chatflow SOP

- [x] Document pre-implementation E2E gate sign-off under
  `artifacts/slices/032-chatflow-sop-integration/032.4/`.
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
