# Customer Assistant UAT Checklist

Scope: browser-only acceptance prep for `/customer-assistant` on the seeded
`refund_baggage_parallel` story.

## Checkpoints

1. Three columns fit in one screen at 1440x900, with internal column scrolling.
2. Default workbench tab is `聚焦`: it shows intent/emotion, handling guidance,
   SOP progress, recommended script actions, and business confirmation cards.
3. The `AI助手` tab is one chat window with a message stream and bottom composer;
   it does not show business confirmation cards, skeleton progress, metrics, or
   worker controls. A seeded follow-up question returns a visible answer and
   source inside that window.
4. The `办理`, `证据`, and `配置` tabs progressively disclose task handling,
   audit/evidence details, and worker configuration. The default `聚焦` tab does
   not expose worker/model/prompt terms.
5. Confirming the pending card from `聚焦` updates the AI assistant card, task
   row, event timeline, and audit evidence in sync.

## Run

```bash
rtk env HIFY_E2E_SCREENSHOT=/tmp/customer-assistant-final-uat.png node frontend/e2e/customer-assistant-final-uat-checkpoints.mjs
```
