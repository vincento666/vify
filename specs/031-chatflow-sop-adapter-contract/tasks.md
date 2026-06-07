# Tasks 031: Chatflow SOP Adapter Contract

## 031.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 030 gates.
- [x] Keep real Chatflow execution out of scope.
- [x] Commit 030-033 spec skeleton documents only.
- [x] Add 031.0 spec sign-off.
- [x] Save documentation-only evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.0/`.
- [x] Confirm no application code, tests, API behavior, or schema changes are
  included in 031.0.

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

- [x] RED: integration tests fail when runtime service is configured with the
  fake adapter port.
- [x] Route selected SOP actions through the adapter port.
- [x] Keep runtime task ledger as source of truth.
- [x] Normalize adapter failures into runtime events and safe responses.
- [x] Save evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.2/`.
- [x] Gates pass.
- [x] Commit 031.2 only.

## 031.3 Dependency-direction gate

- [x] RED: architecture test fails if Workflow/Chatflow imports
  `runtime_lab`.
- [x] Add or update architecture import scan.
- [x] Prove one-way dependency.
- [x] Run targeted runtime-lab tests.
- [x] Save evidence under
  `artifacts/slices/031-chatflow-sop-adapter-contract/031.3/`.
- [x] Add 031 completion sign-off evidence.
- [x] Gates pass.
- [x] Commit 031.3 only.

## Future specs, not 031 tasks

- [ ] Real Chatflow SOP integration.
- [ ] FAQ/RAG/Agent/handoff fallback policy.
