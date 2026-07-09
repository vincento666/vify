# Loop Verifiers

These commands verify Spec 222 slice `222.14.2`.

## RED

```bash
/opt/homebrew/bin/rtk uv run pytest tests/eval/test_ai_assistant_aggregate_production_eval.py::test_aggregate_production_eval_rejects_source_only_runtime_proofs -q
```

Expected RED before implementation:

```text
Source/test-string-only evidence still passes runtime requirements.
```

## Focused Gates

```bash
/opt/homebrew/bin/rtk uv run pytest tests/eval/test_ai_assistant_aggregate_production_eval.py::test_aggregate_production_eval_rejects_source_only_runtime_proofs -q
/opt/homebrew/bin/rtk uv run pytest tests/eval/test_ai_assistant_aggregate_production_eval.py -q
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk uv run ruff check app/modules/ai_assistant/domain/aggregate_production_eval.py tests/eval/test_ai_assistant_aggregate_production_eval.py
/opt/homebrew/bin/rtk uv run python -m py_compile app/modules/ai_assistant/domain/aggregate_production_eval.py tests/eval/test_ai_assistant_aggregate_production_eval.py
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
RED proves source/test-string-only evidence no longer satisfies runtime requirements.
Runtime evidence fixture proves the accepted events/assertions contract.
The five corrective checks no longer read source strings for proof.
Failures include missing_runtime_evidence for absent runtime artifacts.
No company-wide eval framework or unrelated module was changed.
```

Reviewer must verify:

```text
Diff scope is limited to AI Assistant aggregate eval, tests, spec/loop updates.
The runtime evidence contract is explicit and fixture-backed.
No tests or gates are weakened.
No secrets or production behavior are introduced.
```
