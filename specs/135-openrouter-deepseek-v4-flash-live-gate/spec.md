# 135 OpenRouter DeepSeek V4 Flash Live Gate

## Goal

Restore the productized MVP live LLM gate with a real OpenAI-compatible provider by running OpenRouter `deepseek/deepseek-v4-flash` through the customer-assistant, Runtime Lab, and product-chat acceptance paths.

## Scope

- Customer assistant live ReAct gate must run against a real provider and cover task recognition, two-stage recommendation generation, ReAct tool calls, and proposed_action safety boundaries.
- Runtime Lab Chatflow SOP gate must execute real LLM nodes through multi-SOP start, switch, suspend/resume, and completion flows.
- OpenRouter full-chain gate must use the same live model for intent arbitration and Chatflow SOP LLM node execution.
- Product chat live gate must cover direct chat, knowledge/RAG context, workflow LLM node execution, and tool-calling path.
- Evidence must not persist API keys in repo, specs, markdown artifacts, or default local databases.

## Non-Goals

- Do not broaden the MVP feature surface in this slice.
- Do not store provider credentials in demo seed data.
- Do not change frontend UI or visual styles.

## Acceptance

- RED evidence records the pre-fix live gate weakness: two-stage prompts did not provide an exact target JSON for real models, and failed live model attempts were not preserved for ReAct/tool-call diagnosis.
- Unit tests pass for the live gate configuration, redaction, required categories, prompt target JSON, and failed-attempt evidence.
- Local compatible provider acceptance still passes.
- Live OpenRouter DeepSeek V4 Flash gates pass:
  - customer assistant live ReAct/proposed_action acceptance
  - Runtime Lab live Chatflow LLM SOP acceptance
  - Runtime Lab OpenRouter full-chain acceptance
  - product chat live paths
  - base OpenRouter chat/tool-call parser acceptance
- Post-run secret scan reports no real provider key in tracked files, specs, or artifacts.
