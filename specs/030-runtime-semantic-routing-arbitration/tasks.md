# Tasks 030: Runtime Semantic Routing Arbitration

## 030.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 029.8 runtime kernel hardening.
- [x] Keep real Chatflow, FAQ, RAG, Agent, and handoff out of scope.
- [x] Commit 030-033 spec skeleton documents only.
- [x] Add 030.0 spec sign-off.
- [x] Save documentation-only evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.0/`.
- [x] Confirm no application code, tests, API behavior, or schema changes are
  included in 030.0.

## 030.1 Candidate model and score evidence

- [x] RED: unit tests fail for route candidate serialization, score breakdown,
  candidate type validation, and top-k ordering.
- [x] Add candidate domain models for active task, suspended task, SOP intent,
  clarify, and reject-switch candidates.
- [x] Add score breakdown fields for keyword, alias, and mock semantic signals.
- [x] Add top-k candidate merge behavior with stable ordering.
- [x] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.1/`.
- [x] Gates pass.
- [x] Commit 030.1 only.

## 030.2 Explicit cheap signal detector

- [x] RED: unit tests fail for strong SOP keywords, aliases, resume phrases,
  ordinal resume references, and no-op/refusal phrases.
- [x] Implement explicit signal detection as candidate generation.
- [x] Ensure no business slot filling happens in the detector.
- [x] Ensure no-active unambiguous strong SOP candidate can be accepted before
  classifier.
- [x] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.2/`.
- [x] Gates pass.
- [x] Commit 030.2 only.

## 030.3 Mock semantic recall

- [x] RED: unit tests fail for deterministic mock semantic recall against mock
  SOP manifests and suspended task summaries.
- [x] Add mock semantic scoring fixtures for SOP intents.
- [x] Add suspended task summary recall.
- [x] Add active task continuation candidate recall.
- [x] Prove conflicting candidates preserve score evidence and require later
  arbitration.
- [x] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.3/`.
- [x] Gates pass.
- [x] Commit 030.3 only.

## 030.4 Constrained classifier interface

- [x] RED: classifier tests fail for JSON-like output, candidate membership,
  allowed action validation, and low-confidence clarification.
- [x] Add classifier input and result models.
- [x] Add deterministic fake classifier.
- [x] Reject classifier results that select a candidate outside the provided
  finite candidate set.
- [x] Ensure FAQ/RAG document snippets are not classifier inputs.
- [x] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.4/`.
- [x] Gates pass.
- [x] Commit 030.4 only.

## 030.5 Policy gate and runtime integration

- [ ] RED: integration tests fail for no-active early start, no-active conflict,
  active conflict, active non-interruptible switch rejection, and suspended task
  resume.
- [ ] Add pre-classifier policy gate.
- [ ] Add post-classifier policy gate.
- [ ] Integrate candidate recall and classifier into `RuntimeService` without
  moving transaction ownership out of the service.
- [ ] Preserve 029 command idempotency and event sequence behavior.
- [ ] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.5/`.
- [ ] Gates pass.
- [ ] Commit 030.5 only.

## 030.6 API evidence and E2E

- [ ] RED: contract/E2E tests fail for candidate evidence fields and semantic
  route scenarios.
- [ ] Expose candidates, policy gate result, classifier request, and classifier
  result in runtime-lab debug responses.
- [ ] Add API E2E for:
  - no-active alias start;
  - no-active ambiguous candidates with one classifier call;
  - active interruptible semantic switch;
  - active non-interruptible rejected switch;
  - suspended task resume selected from finite candidates.
- [ ] Run targeted runtime-lab tests.
- [ ] Run full backend pytest or document unrelated failures.
- [ ] Save evidence under
  `artifacts/slices/030-runtime-semantic-routing-arbitration/030.6/`.
- [ ] Gates pass.
- [ ] Commit 030.6 only.

## Future specs, not 030 tasks

- [ ] Real Chatflow SOP adapter contract.
- [ ] Real Chatflow SOP integration.
- [ ] FAQ/RAG answer routing.
- [ ] Knowledge/Clarification Agent fallback.
- [ ] Human handoff policy.
