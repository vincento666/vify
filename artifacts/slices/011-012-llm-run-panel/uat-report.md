# Spec 011-012 LLM Run Panel UAT Report

Date: 2026-06-01

## Scope

- Added LLM nodes from the canvas toolbar in both Workflow and Chatflow.
- Configured LLM prompts, connected `START -> LLM -> END`, and ran browser UAT from the right trial-run panel.
- Replaced raw JSON code-block output in the trial-run panel with product-facing result UI:
  - Workflow: status, run id, output key/value rows.
  - Chatflow: status, run id, user/assistant bubbles.

## Observed Outputs

- Workflow LLM run output matched `LLM mock: Workflow LLM UAT <input>`.
- Chatflow LLM run output matched `LLM mock: Chatflow LLM UAT <input> via web`.
- No `.run-result` raw JSON block exists in either trial-run panel.

## Gates

- Frontend unit: `npm run test:unit` passed, 18 files / 34 tests.
- Frontend build: `npm run build` passed.
- Browser e2e/UAT on `http://127.0.0.1:15182` passed:
  - `workflow-chatflow-llm-run`
  - Full Workflow/Chatflow regression set:
    - `workflow-tabs`
    - `workflow-node-interactions`
    - `workflow-canvas`
    - `workflow-config`
    - `workflow-variable`
    - `workflow-test-run`
    - `workflow-publish`
    - `chatflow-entry`
    - `chatflow-shared-graph`
    - `chatflow-variables`
    - `chatflow-conversation-run`
    - `chatflow-publish`

## Local Screenshots

PNG screenshots are generated locally under this folder and intentionally ignored by Git via
`artifacts/**/*.png`.
