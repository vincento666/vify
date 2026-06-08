# Full Backend Gate Note

Command attempted:

```text
rtk env PYTHONPATH=. uv run pytest
```

Result:

- Collected 464 tests.
- The run was manually stopped after several minutes with no new output.
- Output had reached live acceptance tests, ending at
  `tests/acceptance/test_runtime_lab_live_qwen_core_airline_scenarios.py`.
- Targeted 033 runtime-lab, integration, Chatflow SOP adapter, semantic policy,
  and contract gates passed in `final-targeted.txt`.

This is treated as an external/live acceptance gate not completed during 033.
