# Plan

1. Add SDD docs for the unknown `toolPolicyRef` validation slice.
2. Add RED unit coverage around ReAct policy resolution.
3. Add RED MySQL8 API coverage around worker profile update validation.
4. Implement a shared supported-ref list and explicit unknown-ref errors.
5. Run focused unit, integration, and ruff gates.
6. Save evidence under
   `artifacts/slices/158-customer-assistant-worker-tool-policy-ref-validation/158.1/`
   and commit the slice.

## Test Strategy

- Unit: `tests/unit/customer_assistant/test_react_worker.py`.
- Integration: `tests/integration/customer_assistant/test_worker_profiles.py`.
- Ruff: touched domain/test files.

