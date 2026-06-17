# Plan: 150.1 ReAct Tool Policy Runtime Gate

## Slice

Make configured ReAct `toolPolicyRef` affect runtime behavior.

1. Add RED unit coverage for a read tool that should require manual
   confirmation under `manual_confirm_lookup_tools`.
2. Add RED MySQL-backed integration coverage through the worker profile API.
3. Add a small policy resolver in `tool_policy.py`.
4. Let `RestrictedReactWorker` build its default policy from
   `config.tool_policy_ref`.
5. Return `WAITING` with a proposed action before executing tools that require
   manual confirmation.

## Verification

- `rtk env PYTHONPATH=. uv run pytest tests/unit/customer_assistant/test_react_worker.py`
- `rtk env PYTHONPATH=. uv run pytest tests/integration/customer_assistant/test_worker_profiles.py`
- `rtk env PYTHONPATH=. uv run ruff check app/modules/customer_assistant/domain/tool_policy.py app/modules/customer_assistant/domain/react_worker.py tests/unit/customer_assistant/test_react_worker.py tests/integration/customer_assistant/test_worker_profiles.py`

## Result

Completed. Final evidence is saved under
`artifacts/slices/150-customer-assistant-react-tool-policy-runtime-gate/150.1/`.
