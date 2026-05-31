# 010.2 Fixture UAT

- Date: 2026-05-31
- Slice: 010.2 Tool-call parsing
- UAT Type: response fixture

## Expected Result

- OpenAI `tool_calls` responses parse without assistant text.
- Internal call keeps provider call id.
- Function name and JSON arguments are available as structured data.

## Observed Parsed Result

```json
{
  "content": "",
  "finishReason": "tool_calls",
  "tokens": 24,
  "toolCalls": [
    {
      "arguments": {
        "orderId": "A-100"
      },
      "id": "call_1",
      "name": "lookup_order"
    }
  ]
}
```

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Fixture UAT: passed.
