# Builder Handoff — 226.7

TDD method: `tdd`

## Scope

- Replaced the unstable sequence-range processed group with a stable
  `runId/activityId` activity feed.
- Split product-local visual responsibilities into activity feed, activity
  row, durable-plan progress, subagent presence, pure view model and stream
  state composable. Public Agent Harness and Agent Execution remain free of
  product UI.
- Running, queued, approval, failed and cancelled activities default
  expanded. Completed activities default to one collapsed line. Explicit
  overrides win and survive event replay, SSE upsert and durable snapshot
  refresh.
- Streaming model output remains a peer item in the central conversation
  timeline. Final answers remain outside folded execution history.
- Only projected `subagent.execution_*` lifecycles with execution refs enter
  the child presence panel. Running and completed children have separate
  default expansion behavior.
- Restored SSE subscription when reopening an existing durable `RUNNING` run.
- Approval-required events now remain visible in the stable activity and
  expose approve/deny actions without a second detail-fold click.
- Timeline summaries now carry all raw source event IDs. Activity detail
  association uses event-ID set intersection and no sequence-range guess.
- Visuals use existing Hify light tokens and rem dimensions, with keyboard
  focus, ARIA expansion state and reduced-motion fallbacks.

## Observable RED

1. The first focused run failed because `aiAssistantActivityView` and the
   bounded activity components did not exist; four shell contracts also
   failed on the legacy processed group.
2. Browser UAT showed that reopening an existing durable running run loaded a
   snapshot but did not resume SSE.
3. A raw-detail regression test showed that a sequence-range fallback attached
   an unrelated approval event to a tool activity.
4. Browser UAT showed inline approval buttons were hidden behind a second event
   fold.
5. Durable-plan progress RED failed with `activityProgress is not a function`.

All REDs were addressed by the minimum behavior described above.

## GREEN Evidence

- Focused activity/timeline/shell/UAT contracts: `49 passed`.
- Full frontend unit suite: `116 files / 481 tests passed`.
- rem closure: `1 passed`.
- production `vue-tsc && vite build`: PASS.
- repeatable Chromium Browser UAT: PASS.
- `git diff --check`: PASS.

## Browser UAT

Command:

```text
HIFY_E2E_BASE_URL=http://127.0.0.1:5174 \
HIFY_E2E_ARTIFACT_DIR=artifacts/slices/226-ai-assistant-runtime-convergence-shell/226.7 \
node frontend/e2e/ai-assistant-activity-shell-uat.mjs
```

Verified:

- live model text and execution activities share the central timeline;
- running activity expanded;
- completed activity auto-collapsed;
- manual completed override survived stable SSE upsert and snapshot refresh;
- waiting approval and failed activity stayed expanded;
- approval actions were visible in the activity;
- one running and one completed durable child were visible;
- durable plan showed `步骤 1/2`;
- light shell/feed colors, zero page overflow and reduced-motion animation
  fallback.

Artifacts:

- `uat-runs/ai-assistant-activity-shell-uat.json`
- `screenshots/ai-assistant-light-activity-shell.png`
- `screenshots/ai-assistant-approval-error-states.png`

## Explicit Gate Notes

- Backend regression: N/A for this slice. No Python, schema, API response or
  backend event-write behavior changed.
- Live provider: N/A. Browser UAT uses deterministic route fixtures and makes
  zero external provider calls.
- Migration/deploy: N/A. No schema change and no deploy authorization.
- Recursive multi-agent/team UI: out of scope. This slice renders one real
  durable child lifecycle level, as frozen by Spec 226.

## Remaining Contract

- 226.8: caller/contract inventory and evidence-gated removal or isolation of
  duplicate harness, demo/stub registry and compatibility paths.
- 226.9: full cross-module exit matrix and final architecture assessment.
