# Residual Risk

- Real OpenRouter calls are implemented but not part of required gates; standard
  tests use fake OpenAI-compatible clients and deterministic fallback.
- No API key is committed. Operators must provide `OPENROUTER_API_KEY` or
  `HIFY_AI_ASSISTANT_OPENROUTER_API_KEY` at runtime for real Qwen calls.
- Hidden chain-of-thought is not exposed; the UI shows safe Chinese thought
  summaries and model stream chunks only.
- `write_workspace_file` is available as a high-risk tool and remains
  approval-gated by the existing sandbox/approval boundary.
- Existing unrelated dirty `customer_assistant` files are still outside this
  slice and were not touched.
- MySQL currently contains sessions created by development and UAT runs; they
  are persistent records, not mock frontend fixtures, and can be removed with
  the new per-session delete icon.
