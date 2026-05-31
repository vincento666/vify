# 010.1 Fixture UAT

- Date: 2026-05-31
- Slice: 010.1 Tool schema serialization
- UAT Type: request fixture

## Expected Result

- OpenAI chat payload includes `tools`.
- Tool entry uses `type=function`.
- Function schema preserves MCP tool name, description, parameters, and required fields.
- `tool_choice` is `auto`.

## Observed Payload

```json
{
  "messages": [
    {
      "content": "check order A-100",
      "role": "user"
    }
  ],
  "model": "gpt-4.1-mini",
  "tool_choice": "auto",
  "tools": [
    {
      "function": {
        "description": "Look up an order",
        "name": "lookup_order",
        "parameters": {
          "properties": {
            "orderId": {
              "type": "string"
            }
          },
          "required": [
            "orderId"
          ],
          "type": "object"
        }
      },
      "type": "function"
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
