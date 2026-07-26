# Loop State

## RuntimeLab Intent Routing Reliability Program

- date: 2026-07-26
- mode: Closed Loop / Goal accepted
- state: `READY_FOR_228.3_DELIVERY`
- active contract: `specs/228-runtime-policy-replay-and-uncertainty/tasks.md`
- accepted roadmap: `228 -> 229 -> 230 -> 231`
- ADR: `docs/adr/0010-runtime-route-decision-and-execution-boundary.md`
- active unit: `228.3`
- implementation: `228.3` gates complete; selective commit/push pending
- live/paid provider calls: `0`
- production/deploy/PR/merge actions: none
- checker verdict: `228.3 ALL GREEN` (round 4; final exact full integration)
- reviewer verdict: `228.3 PASS` (round 2; 0 findings)

## Contract Matrix

| Spec | Status | Dependency | Next Gate |
|------|--------|------------|-----------|
| 228 Replay and uncertainty | Active; 228.3 Checker green | none | 228.3 Reviewer |
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
- 228.2 recovery round 1: `podman compose ... up -d mysql8` failed while
  pulling `mysql:8.0` with `i/o timeout`.
- 228.2 recovery round 2: direct
  `podman pull docker.io/library/mysql:8.0` failed against
  `registry-1.docker.io:443` with `i/o timeout`.
- Local cache has no MySQL image; no process listens on `127.0.0.1:3306`;
  Homebrew has no MySQL service.
- Read-only follow-up `curl -I https://registry-1.docker.io/v2/` later reached
  the registry and returned expected `401`, so a human-authorized re-entry retry
  may now succeed.
- User authorized starting Hify Docker services and continuing.
- OrbStack is `Running`; the existing compose `mysql8` service is `healthy`.
- `rtk uv run alembic upgrade head` applied through
  `0036_ai_assistant_tenant_scope`; a repository-path-aware `alembic heads`
  reports that single head.
- `rtk uv run alembic check` remains a recorded baseline RED because current
  metadata registration omits existing RuntimeLab/agent execution tables and
  exposes an existing memory-cursor column drift. It is not claimed as PASS and
  did not prevent MySQL migration/connectivity capability recovery.

Unavailable capability is `ENV-BLOCKED-*`, never PASS. The implementation task
must start only the existing local services needed for the active gate and
record the exact recovery command/output.

## Worktree Safety

- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- Worktree:
  `/Users/vincento/.codex/worktrees/560c/hify`
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

## Slice 228.3 Outcome

- shared server-owned uncertainty policy now runs before the mutation gate and
  normalizes low / invalid / incoherent / explicit-clarification results to
  `CLARIFY`.
- bootstrap classifier minimum confidence is now `0.60` in the resolver
  snapshot, and activation rejects `<= 0` thresholds without silently
  rewriting the legacy active row.
- MySQL-backed uncertainty mutation tests prove every uncertainty branch
  clarifies with zero task creation and zero SOP adapter start calls.
- focused unit verifier: PASS (`17 passed`, `8 subtests passed`); focused
  integration verifier: PASS (`32 passed`, `8 subtests passed`); focused E2E:
  PASS (`1 passed`); ruff/diff/secret: PASS.
- independent Checker: `ALL GREEN`; independent Reviewer: pending.

## Next Action

Obtain the independent 228.3 Reviewer verdict. On `PASS`, create the selective
228.3 commit, run the pre-push review gate, push the actual task branch, then
enter the unique 228.4 TDD RED for targeted clarification.
