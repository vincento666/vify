# Loop Verifiers: Spec 225

## Before Every Code Slice

    rtk loop/hooks/skill-preflight.sh --required tdd
    rtk git status --short
    rtk git diff --check

## Focused Unit / Rem

    rtk npm run test:unit -- src/views/workflow/variableCatalog.test.ts src/views/workflow/nodeTestFixtures.test.ts src/views/workflow/workflowCanvasResponsiveLayout.test.ts src/views/workflow/workflowCanvasResponsiveProgressiveCollapse.test.ts
    rtk npm run test:unit -- src/utils/remGovernance.test.ts src/views/workflow/workflowCanvasRemGovernance.test.ts

## Browser / E2E

- Run new focused Spec 225 list-entry, browser geometry, drag, icon, control-rail, and all-node scripts against
  the isolated frontend (`HIFY_E2E_BASE_URL=http://127.0.0.1:15175` for this
  contract session).
- Use the Codex in-app browser for Browser UAT. Save screenshots and logs under
  `artifacts/slices/225-workflow-chatflow-control-hardening/`.
- Workflow and Chatflow lifecycle evidence must cover configuration, save,
  debug, publish, and invoke.

## Live Gate

- The user authorized the configured `qwen/qwen3.5-9b` model only under a USD
  0.10 total cap. Plan at most 15 calls; Intent <=16 output tokens, LLM/Agent
  <=32. Verify a conservative model-pricing upper bound before calling it.
  Stop at the first provider error and do not retry automatically.
- Use redacted prompts/outputs and clean temporary fixtures afterward.
- If provider capability becomes absent, record `ENV-BLOCKED-LIVE-MODEL`; do
  not call a mock path and label it live.

## Final

    rtk npm run build
    rtk git diff --check

Record any unchanged out-of-scope build failure verbatim; do not fix or hide it
under this contract.
