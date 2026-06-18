# Plan 192: AI Assistant Harness UAT Hardening

## Slice 192.1 Approval Decision Continuation

- Add contract RED for approve/deny lifecycle closeout.
- Implement approval resume for approved tools through the existing sandbox,
  registry dispatch, tool-call recording, and run completion.
- Implement denial closeout to `DENIED`.

## Slice 192.2 Inspector Semantics and Usage

- Split pending approval queue from approval history.
- Persist model usage in run responses and expose it through observability.
- Keep frontend types aligned.

## Slice 192.3 Shell Automation and Session Legibility

- Add stable test ids/aria labels for critical controls.
- Surface a useful session subtitle from latest run/input or context where
  available.
- Strengthen browser UAT for copilot-harness readiness.

## Verification

- Backend unit/contract/integration/e2e.
- Frontend unit and `remScaleClosure`.
- Real browser UAT with screenshots and JSON evidence.
- Real OpenRouter Qwen smoke remains environment-gated.
