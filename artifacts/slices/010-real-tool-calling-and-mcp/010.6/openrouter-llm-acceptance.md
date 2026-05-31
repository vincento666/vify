# OpenRouter LLM Acceptance

- Slice: 010.6 live provider acceptance
- Base URL: `https://openrouter.ai/api/v1`
- Model: `xiaomi/mimo-v2-flash`
- API key: runtime environment only, not recorded
- Basic chat: passed
- Tool-call request: passed
- Tool-call parser: passed
- Second LLM round: passed

## Evidence

- Chat token observed: `HIFY_LLM_OK`
- Tool call: `lookup_order`
- Tool arguments: `{"orderId": "A-100"}`
- Final answer excerpt: `The order A-100 is currently **paid** and has an estimated delivery date of **June 2, 2026**.`
