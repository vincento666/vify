# Customer Assistant UAT Checklist

Scope: browser-only acceptance prep for `/customer-assistant` on the seeded
`refund_baggage_parallel` story.

## Checkpoints

1. Three columns fit in one screen at 1440x900, with internal column scrolling.
2. Default workbench tab is `聚焦`: it shows the status bar, intent/emotion,
   business object summary, SOP handling tree, risk/timing card, recommended
   reply card, task ledger, customer draft handling, and sensitive confirmation
   cards.
3. The `AI助手` tab is one chat window with a message stream and bottom composer;
   it does not show business confirmation cards, skeleton progress, metrics, or
   worker controls. A seeded follow-up question returns a visible answer and
   source inside that window.
4. There is no right-side `办理` tab. Handling ledger, recommendation, draft,
   risk, task controls, and high-sensitive actions all live under `聚焦`.
5. The `证据` and `配置` tabs are marked as research/debug entries and still
   expose audit/evidence details and worker configuration. The default `聚焦`
   tab does not expose worker/model/prompt terms.
6. Confirming the pending card from `聚焦` updates the task row, action receipt,
   and audit evidence in sync.

## Run

```bash
rtk env HIFY_E2E_SCREENSHOT=/tmp/customer-assistant-final-uat.png node frontend/e2e/customer-assistant-final-uat-checkpoints.mjs
```
