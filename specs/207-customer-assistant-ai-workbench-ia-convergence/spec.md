# Spec 207: Customer Assistant AI Workbench IA Convergence

Status: Reopened for focus-workbench convergence fixes.
Date: 2026-06-21
Owner: Customer Assistant / Operator Workbench

## Goal

Converge the customer assistant right-side workbench around the operator's
default handling loop. The operator should no longer switch to a separate
`办理` tab for normal closure work, and `聚焦` must not become a pile of copied
business panels. The default `聚焦` tab should answer what the operator should
do now, then expose task intent/SOP progress, passenger-facing reply, risk, and
human confirmation as one traceable flow.

## User Need

When serving a traveler, the operator needs one default place to understand the
task, judge urgency, review the recommended reply, confirm sensitive actions,
and close the work. The AI assistant should be a simple chat surface, while
evidence and configuration stay available as research/debugging entries.

## In Scope

- Right workbench tabs are exactly `聚焦`, `AI助手`, `证据`, and `配置`.
- Remove the right-side `办理` tab and remove `operator-workbench-business-pane`.
- Move task handling closure into `聚焦`:
  - status bar;
  - next best action;
  - top-positioned task intent/SOP handling tree;
  - concise business object and missing-field summary;
  - passenger-facing recommended reply card;
  - sensitive confirmation card with pending-only count;
  - risk and SLA/time-limit card;
  - receipts and detailed controls through progressive disclosure.
- Remove duplicated default focus panels:
  - legacy task ledger as a peer panel;
  - legacy recommendation detail panel;
  - legacy customer reply draft panel;
  - legacy proposed-action detail panel.
- Fix backend/demo blockers required for real UAT:
  - seeded pending action payloads must confirm/reject successfully;
  - live multi-task turns must not trigger the known PyMySQL packet sequence
    500;
  - default worker profiles must not be overridden to stale stub baggage
    profile values;
  - natural refund phrasing such as `退 MU5137 的票` must resolve to refund.
- Keep `AI助手` as a pure chat window with message stream and composer only.
- Mark `证据` and `配置` as research/debugging entry points.

## Out of Scope

- Real RAG, real tool calling, or MCP enhancements.
- Reworking the left session rail or center passenger/operator lanes.
- Large backend architecture rewrites beyond the specific blockers above.

## Acceptance Criteria

- The right-side tab list is exactly `聚焦`, `AI助手`, `证据`, and `配置`.
- `办理`, `business`, and `operator-workbench-business-pane` are absent.
- `聚焦` contains a compact operator handling loop: status/next action,
  top-positioned task intent/SOP tree, business objects/missing fields,
  passenger-facing recommended reply, one sensitive confirmation card,
  risk/time-limit summary, and progressive receipts/details.
- `聚焦` does not render legacy `任务台账`, `坐席建议`, `客户回复草稿`, or `待确认动作`
  as separate default peer panels.
- Recommended reply send/copy/edit actions use the passenger-facing
  `customerReplyDraft`; `operatorRecommendation` is presented as operator
  guidance only.
- The high-sensitive confirmation card counts only `PENDING` actions as pending
  and does not label confirmed/rejected actions as待处理.
- `AI助手` omits the internal header, task/config/metric panels, and business
  state panels. It remains a chat stream plus composer.
- `证据` and `配置` display `研究调试入口`.
- Browser UAT verifies the four-tab IA, focus-first closure path, assistant chat,
  debug entries, seeded action confirmation, and live multi-task turn health.

## Current Problem Inventory

- Problem inventory:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/00-problem-inventory/problem-inventory.md`

## Slice Evidence

- RED: `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`
- View-model RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-b-viewmodel/red.txt`
- Browser UAT RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/red.txt`
- Browser UAT notes:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/uat.md`
- Browser screenshots:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/`

## Final Verification

Final verification is pending for this reopened convergence pass. Required gates:

- Frontend focused unit and full unit.
- `src/remScaleClosure.test.ts`.
- Backend unit/integration/contract/e2e for customer assistant blockers.
- Browser UAT covering all right-side tabs, seeded action confirmation, and live
  multi-task recommendation path.
