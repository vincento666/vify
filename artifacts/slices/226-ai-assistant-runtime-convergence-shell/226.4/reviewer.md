# Reviewer — 226.4

Verdict: `PASS`
Risk: `high`
Review context: `standard`
Goal trust: `PASS` for 226.4; Spec 226 remains `CONTINUE`

Review basis:

- base: `247b7eac`
- branch: `codex/spec-226-agent-harness-convergence`
- merge target: `not-authorized`
- evidence: five observable REDs, Builder handoff, Checker `ALL GREEN`
- context limitation: read-only role separation in the current orchestration
  context; no fresh independent context is claimed or required by this contract.

Findings:

- severity: high
  gate: no-op
  action: no-op
  location: `app/core/host/principal.py`
  evidence: production mode accepts only a typed principal installed in request
    state; configuration rejects production plus local-header identity.
  recommendation: host auth middleware must remain the sole installer of
    `hify_principal` in deployment composition.

- severity: high
  gate: no-op
  action: no-op
  location: `app/modules/ai_assistant/web/router.py`
  evidence: product read/operate permissions are explicit; body actor is
    compatibility input only and mismatch state is auditable.
  recommendation: remove the deprecated body field only through a later public
    API migration.

- severity: high
  gate: no-op
  action: no-op
  location: `app/modules/ai_assistant/infra/repository.py`
  evidence: parent rows carry tenant/user/workspace and dependent reads/writes
    are constrained through scoped runs. Approval/proposed-action write
    predicates found during review were repaired and negatively tested.
  recommendation: keep repository scope mandatory for future child-resource
    additions.

- severity: high
  gate: no-op
  action: no-op
  location: `app/modules/runtime/domain/job_payload.py`
  evidence: raw credential-like fields fail before insert/requeue, while
    explicit references remain serializable.
  recommendation: references must be resolved only inside trusted workers and
    never expanded back into runtime_jobs payloads.

- severity: medium
  gate: no-op
  action: no-op
  location: `app/modules/ai_assistant/runtime_job_worker.py`
  evidence: standalone execution reconstructs scope from the durable run and
    checks job owner/session identity; a mismatched job fails without executing.
  recommendation: 226.5 must add lease fencing to all late-write/effect paths.

- severity: low
  gate: non-blocker
  action: no-op
  location: `app/modules/ai_assistant/web/router.py`
  evidence: router-local executor remains, but it is explicitly frozen for
    replacement in 226.5 and is not mislabeled as HA.
  recommendation: delete executor/lock/in-flight only after durable gateway and
    fault tests are green.

No Critical or open High finding remains. Scope, evidence, and compatibility
claims are consistent with Spec 226. Recommendation: enter the selective Slice
Commit Gate, staging only 226.4 implementation, tests, evidence, and Loop
pointers.
