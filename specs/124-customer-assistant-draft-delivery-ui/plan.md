# Plan: Customer Assistant Draft Delivery UI

## Slice 124.1

Expose the backend draft-delivery outbox in the existing proposed-action panel
with one compact control and receipt, keeping the operator confirmation flow
intact.

## Approach

1. Add failing API/runtime/panel tests.
2. Add a typed `deliverCustomerAssistantAction` API method.
3. Add `deliverCustomerAssistantRuntimeAction` using the existing ledger
   refresh path.
4. Add a delivery-only button for confirmed `send_customer_message` actions.
5. Show a compact sent/failed delivery receipt from action result payload.
6. Add a browser UAT that creates a draft action, confirms it, delivers it, and
   checks events/audit/results.

## Test Strategy

- Focused unit:
  - `frontend/src/api/customerAssistant.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantRuntime.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
- Rem gate:
  - `frontend/src/remScaleClosure.test.ts`
  - `frontend/src/utils/remGovernance.test.ts`
- Browser UAT:
  - `frontend/e2e/customer-assistant-draft-delivery-ui.mjs`

## Risks

- Action result payloads differ between normal execution and draft delivery;
  keep delivery receipt parsing defensive.
- The proposed-action panel is dense; use existing receipt/action styles.
- Delivery is a write operation, so the button must remain operator-only and
  require confirmed action status.
