# Plan

1. Create SDD docs and evidence directory.
2. Run the qwen/qwen3.5-9b live OpenRouter gates with credentials only
   in process environment.
3. Wrap database-backed live gates with disposable MySQL8 databases.
4. Scan artifacts for API key material.
5. Update docs and commit tracked SDD.

## Test Strategy

- `tests/acceptance/test_customer_assistant_live_react_acceptance.py`
- `tests/acceptance/test_runtime_lab_live_chatflow_llm_sop.py`
- `tests/acceptance/test_runtime_lab_live_openrouter_full_chain.py`
- `tests/acceptance/test_runtime_v2_live_openrouter_llm.py`
- `tests/acceptance/test_openrouter_product_chat_paths.py`
- `tests/acceptance/test_openrouter_llm_acceptance.py`
