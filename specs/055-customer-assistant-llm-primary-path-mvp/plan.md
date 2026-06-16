# Plan 055: Customer Assistant LLM Primary Path MVP

## Architecture

Reuse the 047 shadow client and parsers, but add a decision layer:

```text
deterministic baseline
  + LLM candidate
  + schema validator
  + safety validator
  + confidence/fallback policy
  -> selected commands/recommendation
```

The selected output must be recorded as runtime events.

The recommendation prompt/schema is also the compatibility foundation for later
Two-Stage ReAct finalization. It must stay strict JSON, evidence-bound, and
compatible with the deterministic recommendation result shape.

## Settings

Add customer-assistant scoped settings:

```text
HIFY_CUSTOMER_ASSISTANT_LLM_RUNTIME_MODE=deterministic|shadow|llm_primary_with_fallback
HIFY_CUSTOMER_ASSISTANT_LLM_PRIMARY_MODEL_CONFIG_ID=<id>
HIFY_CUSTOMER_ASSISTANT_LLM_PRIMARY_MIN_CONFIDENCE=0.70
```

## Tests

Use fake LLM clients for default gates:

- valid LLM primary task recognition;
- malformed JSON fallback;
- unsupported command fallback;
- low confidence fallback;
- recommendation primary success;
- recommendation fallback;
- proposed action safety still enforced.

## Browser UAT

Run with fake primary mode first. Optional live UAT can be run when a provider
config is available.
