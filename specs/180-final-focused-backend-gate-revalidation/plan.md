# Plan

1. Create SDD docs and evidence directory.
2. Run focused customer-assistant backend gates.
3. Run focused Runtime Lab SOP/runtime-v2 gates.
4. Run focused workflow/chatflow runtime v2 gates.
5. Run focused MySQL8 gates.
6. Update evidence status and commit the tracked SDD.

## Test Strategy

- Customer assistant:
  `tests/integration/customer_assistant/test_worker_profiles.py`,
  `tests/integration/customer_assistant/test_proposed_action_atomic_mutations.py`,
  `tests/integration/customer_assistant/test_operator_knowledge_qa.py`,
  `tests/contract/customer_assistant/test_customer_assistant_api.py`,
  `tests/e2e/customer_assistant/test_customer_assistant_react_worker_sse.py`.
- Runtime Lab:
  `tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py`,
  `tests/integration/runtime_lab/test_runtime_lab_sop_adapter_contract.py`,
  `tests/integration/runtime_lab/test_chatflow_trace_api.py`.
- Workflow/chatflow:
  selected runtime v2 facade/lifecycle/versioning/node tests.
- MySQL8:
  `tests/unit/core/test_mysql8_database_boundary.py`,
  selected `tests/integration/mysql8/*`.

