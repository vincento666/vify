# Plan

1. Add SDD docs for risk policy ref validation.
2. Add RED MySQL8 API coverage for unknown `riskPolicyRef`.
3. Implement a shared supported-risk-policy list and service-layer validation.
4. Run focused integration and ruff gates.
5. Save evidence under
   `artifacts/slices/177-customer-assistant-worker-risk-policy-ref-validation/177.1/`
   and commit the slice.

## Test Strategy

- Integration: `tests/integration/customer_assistant/test_worker_profiles.py`.
- Ruff: touched service/risk-policy/test files.

