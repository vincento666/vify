# 034.4 Badcases And Fixes

## Routing And Intent

- `取消行程` and `航班取消` were treated as refusal because `取消` was in the
  no-op phrase list. Removed the broad refusal term and kept explicit no-op
  phrases only.
- `航班取消了，我需要改签或补偿方案` routed to `change_flight` because the broad
  strong keyword `改签` tied with `航班取消`. Kept `改签` as an alias and reserved
  strong change-flight triggers for more explicit phrases.
- `特殊服务` missed `special_assistance`; added vocabulary coverage.
- `补登里程，登机牌还在` routed to seat/check-in because `登机牌` was too strong.
  Removed it from seat strong triggers and added stronger membership mileage
  vocabulary.

## Runtime And Chatflow

- The browser UAT env fixture wrote JSON without shell quoting, so sourcing it
  produced `{refund_ticket:1}` and the runtime-lab service failed parsing. Added
  robust JSON/comma/braced binding parsing and wrote quoted evidence env.
- Chatflow resume exposed only `conversation` scoped variables to the runtime
  adapter in some paths. `order_no` collected by an information-collection node
  without `targetScope` was lost, so confirmation resumed back to information
  collection. Fixed the runtime-lab Chatflow adapter to merge available
  `node_outputs.*.collected` and to parse business variables from the user
  collection turn into the checkpoint.

## Evidence

- Backend scale gate: `backend-scale.txt`.
- Runtime-lab regression: `backend-runtime-lab-regression.txt`.
- Chatflow regression: `backend-chatflow-regression.txt`.
- Workflow/chatflow regression: `backend-workflow-chatflow-regression.txt`.
- Frontend full unit and REM gate: `frontend-unit-full.txt`.
- Browser UAT report: `browser-uat.md`.
