# Exit Matrix — Spec 226

Date: 2026-07-18

| Gate | Result | Evidence |
|---|---|---|
| Worker crash/takeover/lease fencing/late-write | PASS | HA matrix `47 passed`; runtime-job integration `13 passed` |
| Principal spoof/cross-scope/approval replay | PASS | security matrix `35 passed, 4 subtests passed` |
| Agent Harness/Execution dependency direction | PASS | public boundary matrix `13 passed`; static dependency search clean |
| AI Assistant unit/contract/integration/E2E/eval | PASS | first sweep found only two stale demo fixtures; corrected integration suite `35 passed`; all observed failures closed |
| Customer Assistant unit/contract/integration/E2E | PASS | `166 passed, 2 skipped, 15 subtests passed` |
| Runtime V2 218/219 | PASS | unit `24`; runtime contracts `31`; runtime-job contracts `15`; runtime-job integration `13`; exclusive runtime integration `35` |
| Frontend unit/build/rem | PASS | `116 files / 482 tests`; production build PASS; rem governance included |
| Browser UAT | PASS | light theme, live text/activity peers, running expanded, completed collapsed, override persistence, approval/error, running/completed child, reduced motion, no overflow |
| Migration graph and reversibility | PASS | one head at 0036; disposable-MySQL migration contracts `3 passed` |
| Static/diff/secret checks | PASS | Ruff, diff check, dependency audit and added-line secret scan |
| Live provider | N/A | frozen external-call budget is zero |
| Production migration/deploy/load/SLA | N/A | outside authorized local refactor contract |

## Browser Evidence

- `../226.7/uat-runs/ai-assistant-activity-shell-uat.json`
- `../226.7/screenshots/ai-assistant-light-activity-shell.png`
- `../226.7/screenshots/ai-assistant-approval-error-states.png`
- 226.8 repeated the UAT after cleanup and also verified Add Context is absent.

## Operational Follow-ups

1. Run the migration/deployment plan in the target environment under separate
   release authorization.
2. Close the external-consumer inventory before physically deleting
   `/worker/process`; current target is 2026-08-01.
3. If production-grade parity with Codex/Claude Code is the next goal, open a
   new contract for true spawn/steer/cancel/nested multi-agent orchestration,
   infrastructure sandboxing and multi-host SLO/load evidence.
4. Authorize a non-zero provider budget before running live quality/cost gates.
