# Plan — Spec 228

## Design Summary

Repair evaluation truth before changing routing behavior. Runtime policy
governance owns evaluation orchestration and persistence, but receives a
`RuntimeRouteReplayPort`; it does not import RuntimeLab implementation details.
RuntimeLab supplies the adapter at composition time.

```text
RuntimePolicyReplayService
  -> RuntimeRouteReplayPort
       -> shared RuntimeRouteDecisionEngine
            <- RuntimeLabService
```

The current `_semantic_decision()` may be extracted only as far as required to
establish this shared seam. This is not authorization to refactor unrelated
`RuntimeLabService` behavior.

## 228.1 Evaluation Runner

Add a small evaluation contract capable of single- and multi-turn cases.
Required cases initially reuse the 040 confusion/fallback matrices and the 030
semantic-policy invariants. Known-gap cases cover:

- real LLM low confidence;
- explicit `needs_clarification`;
- targeted clarification loss;
- duplicate multi-source candidates;
- multi-turn ellipsis;
- intent/catalog separation;
- unauthorized mutation;
- `"我想退费并开发票"` composite flattening.

RED:

- evaluation expects an injected decision runner and fails because governance
  currently computes its own answer;
- a deliberately wrong runner result must fail the report;
- missing required evidence must fail rather than disappear from counts.

GREEN:

- deterministic report model;
- no live provider dependency;
- report retains per-case actual route evidence and aggregate metrics.

## 228.2 Governance Integration

Replace `_candidate_decision()` use with the injected replay port. Preserve
existing evaluation-run APIs and storage shape when possible. If additional
JSON report fields fit existing columns, no migration is allowed.

Required parity:

- direct shared decision-engine result equals evaluation result;
- MySQL-backed `RuntimeLabService.handle_command()` integration result equals
  the shared decision result for representative no-active, active, suspended,
  FAQ/SOP, RAG/SOP, and handoff cases;
- a candidate profile snapshot, not the currently active profile, is evaluated;
- historical decision logs retain old-vs-candidate comparison semantics.

## 228.3 Uncertainty Policy

Introduce one post-classifier `UncertaintyPolicy` shared by fake and real LLM
classifiers. It normalizes result coherence, applies the configured confidence
threshold, and returns either the original finite selection or a CLARIFY
result.

Run this policy before `_recover_clarify_result()` and Policy Gate. Recovery
must not override an explicit uncertainty verdict. Any remaining technical
fallback is sent through the same policy.

Update runtime-policy bootstrap and validation:

- bootstrap `classifierMinConfidence = 0.60`;
- API schema remains `0..1` for read compatibility;
- release validation rejects `<= 0` for new activation;
- old stored profiles are neither mutated nor mislabeled as newly validated.

## 228.4 Clarification Projection

Add `clarification_question` to `RouteDecision`, decision serialization,
command replay, decision logs, TypeScript route types, and the RuntimeLab
inspector. The assistant reply uses the normalized targeted question.

The existing menu is fallback copy only. It is not appended when a targeted
question exists.

Browser UAT covers:

1. low-confidence transactional selection;
2. high-confidence output with `needs_clarification=true`;
3. invalid/empty question fallback;
4. idempotent replay showing identical question and no task mutation.

## Verification Strategy

- Unit: evaluator, uncertainty policy, result validation, resolver defaults.
- Integration: real MySQL RuntimeLab route parity and mutation counters.
- Contract: runtime-policy replay API, config API, additive route fields.
- E2E: semantic API plus fallback/confusion matrices.
- Browser: RuntimeLab chat, targeted question, unchanged active/suspended
  state.
- Review: contract scope, false-green threat model, secret scan, diff check.

## Rollback

- evaluation adapter can be reverted without changing stored historical runs;
- additive API fields can remain nullable;
- bootstrap threshold rollback requires an explicit policy decision and cannot
  bypass release validation;
- no destructive data migration is planned.

## Risks

- sharing the decision engine may accidentally broaden a service refactor;
- replay may accidentally mutate real session state;
- legacy zero-threshold profiles may be confused with newly validated profiles;
- clarification recovery may reintroduce mutation through another path.

Mitigations: narrow seam, rollback-only/disposable integration sessions,
explicit legacy status, negative mutation counters, independent review.
