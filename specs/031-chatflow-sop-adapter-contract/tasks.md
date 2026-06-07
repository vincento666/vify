# Tasks 031: Chatflow SOP Adapter Contract

## 031.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 030 gates.
- [x] Keep real Chatflow execution out of scope.
- [x] Commit 030-033 spec skeleton documents only.

## 031.1 Adapter port and DTOs

- [x] Blocked until 030 completion gate passes.
- [x] RED: adapter contract tests fail for start, continue, suspend, resume,
  failure normalization, and checkpoint serialization.
- [x] Define adapter request, result, status, and checkpoint DTOs.
- [x] Add fake adapter implementation.
- [x] Save evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.1/`.
- [x] Gates pass.
- [x] Commit 031.1 only.

## 031.2 Runtime service adapter boundary

- [ ] RED: integration tests fail when runtime service is configured with the
  fake adapter port.
- [ ] Route selected SOP actions through the adapter port.
- [ ] Keep runtime task ledger as source of truth.
- [ ] Normalize adapter failures into runtime events and safe responses.
- [ ] Save evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.2/`.
- [ ] Gates pass.
- [ ] Commit 031.2 only.

## 031.3 Dependency-direction gate

- [ ] RED: architecture test fails if Workflow/Chatflow imports
  `runtime_lab`.
- [ ] Add or update architecture import scan.
- [ ] Prove one-way dependency.
- [ ] Run targeted runtime-lab tests.
- [ ] Save evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.3/`.
- [ ] Gates pass.
- [ ] Commit 031.3 only.

## Future specs, not 031 tasks

- [ ] Real Chatflow SOP integration.
- [ ] FAQ/RAG/Agent/handoff fallback policy.
