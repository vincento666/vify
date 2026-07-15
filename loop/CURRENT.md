# Current Loop Scope: Spec 225 Workflow/Chatflow Control Hardening

## Status

    mode: Closed Loop
    current unit: 225.5 Live Intent binding and Runtime V2 parity
    implementation: 225.5 Runtime V2 Intent/model-binding, provider
    credential-readiness, and Runtime V2 terminal-output projection pass; the
    user-authorized 15-call live matrix is complete with clean fixtures

## Active Contract

    specs/225-workflow-chatflow-control-hardening/spec.md
    specs/225-workflow-chatflow-control-hardening/plan.md
    specs/225-workflow-chatflow-control-hardening/tasks.md
    artifacts/slices/225-workflow-chatflow-control-hardening/contract/contract.md

## Branch Preflight

    worktree: /private/tmp/hify-workflow-chatflow-control-hardening
    branch: codex/workflow-chatflow-control-hardening
    base: 1ee8dc5e
    merge target: not selected
    dirty at contract start: no tracked changes

## Frozen Scope

- `frontend/src/views/workflow/` Workflow/Chatflow list and shared canvas/control code;
- `app/modules/workflow/domain/runtime_v2.py` and focused runtime tests for the
  LLM Intent completer wiring;
- provider credential-readiness reporting/client preflight and focused
  provider/chat tests, limited to the live-gate defect found in Browser UAT;
- focused frontend tests and Workflow/Chatflow E2E scripts;
- Spec 225 docs, loop state, and Spec 225 evidence.

Excluded: API/schema/dependency work, broader runtime behavior, broader list
redesign, and the dirty original worktree.

## Stop Conditions

- The repair needs a public contract, runtime, schema, dependency, or product
  information-architecture change.
- A new UI fixture cannot clean up its own test data on failure.
- The same RED persists through two focused implementation attempts.
- The user-authorized 15 planned model calls, 16-token Intent / 32-token
  LLM+Agent limits, or the USD 0.10 cap would be exceeded; stop before
  requesting more.
- Canonical async Runtime V2 cannot execute the focused completer regression or
  the Intent selector cannot persist its binding after two TDD attempts.
- Required browser, provider, or verification evidence is unavailable.
- Do not exceed the user-approved 15 planned live completions or USD 0.10 cap.

## Next Action

The provider is configured externally and connection discovery passes. The
Workflow and Chatflow draft and published Runtime V2 paths complete
successfully. The user explicitly increased the live call limit from 12 to 15
after the Chatflow terminal-output projection repair; all 15 compact calls
completed without retry or provider error, and temporary fixtures are clean.
Credentials remain external and are never written into this worktree. All
evidence remains under `artifacts/slices/225-workflow-chatflow-control-hardening/`.
