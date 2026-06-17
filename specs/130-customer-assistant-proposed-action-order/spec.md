# 130 Customer Assistant Proposed Action Order

## Status

Slice 130.1 complete. Customer-assistant proposed actions now use a stable
service-layer product order: task controls first, business write actions next,
and reply-draft delivery actions last.

## Goal

Keep customer-assistant proposed actions product-stable after reply-draft
delivery actions are added. Business/task actions must remain first in turn
results and action APIs, while customer reply draft delivery actions stay
visible but do not displace the primary operator decision.

## Acceptance Criteria

- Existing customer-assistant E2E fails before the fix because
  `send_customer_message` appears before `submit_refund`.
- Turn results and list-proposed-actions responses order task-control actions
  first, business write actions second, and reply-draft delivery actions last.
- The reply-draft delivery flow from slice 126 remains present and confirmable.
- Customer-assistant e2e, integration, contract, and Ruff gates pass.

## Non-goals

- Do not change persistence order, action ids, audit event order, or delivery
  outbox behavior.
- Do not change frontend UI or visual styles.

## Evidence

Evidence lives under
`artifacts/slices/130-customer-assistant-proposed-action-order/130.1/`.

- RED: `red.txt`
- Focused E2E: `focused-e2e.txt`
- Customer-assistant E2E: `customer-assistant-e2e.txt`
- Customer-assistant integration: `customer-assistant-integration.txt`
- Customer-assistant contract: `customer-assistant-contract.txt`
- Ruff: `ruff.txt`
