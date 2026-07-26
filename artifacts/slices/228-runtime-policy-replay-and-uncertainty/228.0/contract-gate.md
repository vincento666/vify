# Contract Gate Evidence — RuntimeLab Intent Routing Reliability Program

Date: 2026-07-26

## Delivery Scope

- Specs 228-231 and ADR 0010 only;
- `specs/README.md` natural order/index;
- `loop/CURRENT.md`, `loop/STATE.md`, and `loop/VERIFIERS.md`;
- this Contract Gate evidence.

No implementation, test weakening, provider call, PR, merge, deploy, production
write, or migration application occurred during contract authoring.

## Branch Preflight

- branch: `codex/spec-228-runtime-lab-intent-routing-reliability`
- worktree:
  `/Users/vincento/work/develop/hify-spec-228-runtime-lab-intent-routing`
- base: `815cb1c90031a9dfb1e11e325a1ecf6ed48c0441`
- merge target: `not-authorized`
- original dirty checkout remained untouched.
- IDs start at 228 because the original checkout already contains concurrent
  Spec 227 work; its number remains reserved.

## Contract Decisions

- S0-S6 map to Specs 228-231 in strict Goal Gate order.
- Chatflow remains child SOP execution-state source of truth.
- runtime-policy evaluation must call the shared production decision
  implementation.
- uncertainty, candidate margin, execution authority, and composite resolution
  are separate fail-closed gates.
- Intent Catalog is code-first; IntentRetriever is isolated from FAQ/RAG answer
  knowledge and requires zero live provider calls.
- composite intent creates a bounded route-ledger plan, not a second workflow
  runtime.
- commit/push authorized; PR/merge/deploy/live-provider unauthorized.

## Local Author Checks

Completed before independent review:

- `rtk git status --short --branch`
- `rtk git diff --check`
- required existing document/test parent paths checked;
- branch/worktree/base pointers checked;
- S0-S6, dependency, `WAITING_HUMAN`, budget, and authority terms scanned;
- scoped credential-pattern scan returned no candidate secret.

Read-only baseline unit command:

```text
rtk uv run pytest tests/unit/runtime_policy/test_replay_service.py \
  tests/unit/runtime_policy/test_governance_validation.py \
  tests/unit/runtime_lab/test_constrained_classifier.py \
  tests/unit/runtime_lab/test_candidates.py \
  tests/unit/runtime_lab/test_mock_semantic_recall.py -q --tb=short
```

Result: `23 passed, 1 warning, 2 subtests passed`. The warning is the existing
Starlette `httpx` TestClient deprecation warning.

Contract documents do not constitute implementation or behavioral PASS.

## Independent Gates

- First review: findings raised for an unfrozen `CONDITIONAL` composite
  relation, over-broad RuntimeLab endpoint security wording, missing read-answer
  ownership, and ambiguous child-effect classification.
- Repairs: removed `CONDITIONAL`; narrowed Spec 230 to conversation/session
  surfaces while retaining the admin endpoints as an explicit follow-up; added
  the read-answer gate; defined server-owned external/delegated/internal node
  classes and matching verifier families.
- Checker second pass: `ALL GREEN`.
- Reviewer second pass: `PASS`.
- Remaining P0-P2 findings: none.

The Contract Gate is complete. Active state is
`READY_FOR_228.1_CAPABILITY_RECOVERY_AND_TDD`.
