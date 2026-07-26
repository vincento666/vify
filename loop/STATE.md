# Loop State

## RuntimeLab Intent Routing Reliability Program

- date: 2026-07-26
- mode: Closed Loop / Goal accepted
- state: `READY_FOR_228.1_CAPABILITY_RECOVERY_AND_TDD`
- active contract: `specs/228-runtime-policy-replay-and-uncertainty/tasks.md`
- accepted roadmap: `228 -> 229 -> 230 -> 231`
- ADR: `docs/adr/0010-runtime-route-decision-and-execution-boundary.md`
- active unit: `228.1`
- implementation: not started
- live/paid provider calls: `0`
- production/deploy/PR/merge actions: none
- checker verdict: `ALL GREEN`; publish gate: `PASS`
- reviewer verdict: `PASS`

## Contract Matrix

| Spec | Status | Dependency | Next Gate |
|------|--------|------------|-----------|
| 228 Replay and uncertainty | Accepted; active | none | 228.1 TDD RED |
| 229 Routing reliability | Accepted; waiting | Spec 228 Goal Gate | 229.1 TDD RED |
| 230 Execution boundary | Accepted; waiting | Spec 229 Goal Gate | 230.1 security RED |
| 231 Composite intent | Accepted; waiting | Spec 230 Goal Gate | 231.1 TDD RED |

Contract files do not constitute Unit, Integration, Contract, E2E, Browser UAT,
security, migration, or production PASS.

## Confirmed Baseline Facts

- runtime-policy governance replay currently has a parallel
  `_candidate_decision()` path.
- real LLM classifier output does not yet share the fake classifier's minimum
  confidence enforcement.
- candidate sources can present the same target more than once before Top-K.
- RuntimeLab currently derives only limited active/suspended context for
  semantic arbitration.
- intent-selection knowledge is distributed across SOP manifests and recall
  constants rather than one versioned catalog.
- a valid route decision currently reaches task/adapter mutation without a
  separate trusted principal/permission gate.
- route-model connectivity and fallback-agent administration are existing
  access-control gaps outside Spec 230's conversation/session execution scope;
  final reporting must keep this follow-up explicit.
- the regression `"我想退费并开发票"` currently permits a single
  `invoice_apply` selection instead of preserving both atomic components.

These facts are frozen as RED targets; implementation must re-read the current
code before writing and record exact symbols/lines in slice evidence.

## Capability Snapshot

- Python/`uv`, Node/`npm`, Docker and Podman are installed.
- At contract creation, MySQL on `127.0.0.1:3306` was unavailable.
- The repository already provides
  `docker-compose.mysql8-weaviate.yml` with service `mysql8`; bounded local
  capability recovery is in scope.
- Hify backend and Browser UAT server were not running at contract creation.
- Live provider capability is intentionally N/A because budget is zero.

Unavailable capability is `ENV-BLOCKED-*`, never PASS. The implementation task
must start only the existing local services needed for the active gate and
record the exact recovery command/output.

## Worktree Safety

- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability`
- Worktree:
  `/Users/vincento/work/develop/hify-spec-228-runtime-lab-intent-routing`
- Base: `815cb1c90031a9dfb1e11e325a1ecf6ed48c0441`
- Merge target: `not-authorized`
- The original dirty Hify checkout remains out of scope and untouched.
- Selective staging must include only the active contract/slice.

## Goal Controls

- max attempts: 3 per slice; 2 for repeated Spec 230 security finding family
- TTL: 21 days from first implementation write
- provider budget: 0
- exhaustion: `WAITING_HUMAN`
- independent Checker and Reviewer: required
- Spec 230 review: fresh-required

## Next Action

Finish Contract Gate review and record evidence. After contract commit/push,
the new task must run Branch Preflight, restore MySQL capability if required,
invoke `tdd`, and produce the `228.1` false-green RED before implementation.
