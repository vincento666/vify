# Tasks 041: Runtime Policy Config And Observability

## 041.0 Spec And Boundary

- [x] Confirm 041 numbering is unused.
- [x] Define backend-only configuration and observability scope.
- [x] Confirm no frontend work in 041.
- [x] Confirm 042 owns release gate and rollback.

## 041.1 Runtime policy profile model and API

- [x] RED: profile CRUD API does not exist.
- [x] RED: invalid profile threshold/config payload is accepted.
- [x] Add `RuntimePolicyProfile` table/repository/service.
- [x] Add request/response schemas for thresholds, classifier, FAQ, RAG,
  fallback Agent, and handoff config.
- [x] Add profile CRUD API.
- [x] Save RED/GREEN evidence under
  `artifacts/slices/041-runtime-policy-config-observability/041.1/`.
- [ ] Commit 041.1 only.

## 041.2 Effective policy resolver

- [x] RED: runtime-lab cannot resolve active profile by tenant/bot/channel/session.
- [x] RED: env settings are still the only classifier/FAQ/RAG source.
- [x] Add `RuntimePolicyResolver`.
- [x] Add env bootstrap fallback when no active profile exists.
- [x] Add effective-profile API.
- [x] Save evidence under
  `artifacts/slices/041-runtime-policy-config-observability/041.2/`.
- [ ] Commit 041.2 only.

## 041.3 Classifier and fallback Agent config factories

- [ ] RED: LLM classifier prompt/model/runtime params cannot come from profile.
- [ ] RED: runtime API always instantiates `FakeFallbackAgent`.
- [ ] Add profile-driven classifier factory.
- [ ] Add profile-driven fallback Agent factory for `fake`, `llm_agent`,
  `existing_agent`, and `external_webhook` config shapes.
- [ ] Keep unsupported live adapters safely disabled until configured.
- [ ] Save evidence under
  `artifacts/slices/041-runtime-policy-config-observability/041.3/`.
- [ ] Commit 041.3 only.

## 041.4 Decision log persistence and query API

- [ ] RED: route decision log lacks policy snapshot.
- [ ] RED: decision-log API cannot filter by session/profile/action/source/time.
- [ ] Add `RuntimeDecisionLog` table/repository/service.
- [ ] Persist effective policy snapshot for each runtime-lab message.
- [ ] Persist route evidence and layer-level confidence signals.
- [ ] Add decision-log query APIs.
- [ ] Prove default 040 route matrix remains compatible.
- [ ] Save evidence under
  `artifacts/slices/041-runtime-policy-config-observability/041.4/`.
- [ ] Commit 041.4 only.
