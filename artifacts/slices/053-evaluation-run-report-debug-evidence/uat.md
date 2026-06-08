# 053 Evaluation Run Report Debug Evidence

Date: 2026-06-08

Scope:

- Restore the frontend full gate by adding the missing run-report target debug evidence helpers expected by existing tests.

Checks:

- RED: `runReportViewModel.test.ts` failed because `targetEvidenceActionLabel` was not exported.
- Unit: focused `runReportViewModel.test.ts` passed after the fix.
- Full frontend unit passed.
- Frontend build passed.

Behavior:

- Workflow failed-case evidence action label: `查看 Workflow 调试`.
- Chatflow failed-case evidence action label: `查看 Chatflow 调试`.
- Unsupported targets or empty debug URLs return no action label.
- Debug href returns the provided `targetDebugUrl`.
