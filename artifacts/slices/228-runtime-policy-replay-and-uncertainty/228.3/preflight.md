# 228.3 TDD Preflight

- Method: `tdd`
- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- HEAD: `0eaafa65`
- Worktree: isolated Codex worktree; clean before the first RED write
- Base/merge target: frozen program base; merge not authorized
- Required capability: local MySQL `mysql8` healthy
- Live/paid provider budget: `0`; deterministic classifier fixtures only
- Repair budget: 3 directed rounds

## Observable seam

- `LlmConstrainedIntentClassifier.classify()` validates finite-candidate
  membership but does not enforce confidence or result coherence.
- `RuntimeLabService._semantic_decision()` calls
  `_recover_clarify_result()` before the policy gate, so an explicit real-LLM
  clarification can become a task-mutating action.
- The environment bootstrap profile still publishes
  `classifierMinConfidence = 0.0`.
- Release activation does not reject a newly activated profile whose threshold
  is `<= 0`.

## RED target

Add focused unit and MySQL integration tests proving that low, non-finite,
out-of-range, explicit-clarification, and incoherent classifier results must
produce `CLARIFY` with zero task creation, zero child adapter invocation, and no
recovery into a mutating route. Add resolver/release tests proving a `0.60`
bootstrap and fail-closed new activation without silently editing legacy rows.
