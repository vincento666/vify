# RuntimeLab Live OpenRouter Full Chain Acceptance

- Slice: 034.11 live full-chain gate
- Entry: `/api/v1/runtime-lab/sessions/{id}/messages`
- Intent arbitrator: live OpenRouter single target model
- SOP execution: live provider-backed Chatflow `LLM` nodes
- Base URL: `https://openrouter.ai/api/v1`
- Target arbitrator model: `qwen/qwen3.5-9b`
- High-intelligence optional model: `deepseek/deepseek-v4-flash`
- Arbitrator success model: `qwen/qwen3.5-9b`
- Chatflow SOP LLM model: `qwen/qwen3.5-9b`
- API key: runtime environment only, not recorded
- Switch action: `SUSPEND_AND_START`
- Switch classifier mode: `llm`

## Arbitrator Attempts

- `qwen/qwen3.5-9b`: passed

## Live SOP LLM Replies

- `COMPLETE_TASK`: 发票申请完成 marker=HIFY_INVOICE_APPLY_LIVE phone=13900000003
- `COMPLETE_TASK`: 退票完成 marker=HIFY_REFUND_TICKET_LIVE phone=13900000001

## Badcases and Fixes

- qwen first returned only reasoning and no text content when the arbitrator
  request used `max_tokens=400`; fixed the test-stage single-model arbitrator
  by setting `reasoning.effort=none`, `reasoning.exclude=true`, and
  `max_tokens=1200`.
- qwen/DeepInfra rejected multi-system-message Chatflow requests and the SOP
  marker was empty; fixed the live SOP fixture by leaving the seeded default
  agent system prompt empty, keeping the node `systemPrompt` as the single
  system message, disabling reasoning through model `extra_params`, and raising
  the LLM node `maxTokens` to 1200.
