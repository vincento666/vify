# Loop Verifiers

These commands verify Spec 222 slice `222.14.4`.

## RED

```bash
HIFY_RUN_LIVE_AI_ASSISTANT=1 OPENROUTER_API_KEY=[REDACTED] /opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_live_qwen36_real_case_uat.py -q -s
```

Expected RED before implementation:

```text
This slice is a live rerun gate; missing key/network/quota/model availability must be recorded as blocked, not PASS.
```

## Focused Gates

```bash
HIFY_RUN_LIVE_AI_ASSISTANT=1 OPENROUTER_API_KEY=[REDACTED] /opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_live_qwen36_real_case_uat.py -q -s
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
Live gate used qwen/qwen3.6-27b through OpenRouter.
Pure text case produced raw stream chunks before model completion.
Mock aviation refund/change/baggage/flight disruption cases completed.
Approval path, audit redaction, token/cost/context budget were validated.
Artifacts do not contain the API key.
```

Reviewer must verify:

```text
Diff scope is limited to spec/loop state because this slice is a live rerun.
No provider/model expansion, real airline integration, or code change was introduced.
No secrets are committed or copied into artifacts.
The artifact states PASS only because the real live gate passed.
```
