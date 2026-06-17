# 135 Plan

## Slice 135.1 Live Gate Hardening And Evidence

1. Reproduce live gate failure with DeepSeek V4 Flash.
2. Add focused RED tests for the observed gate defects.
3. Harden the acceptance gate without weakening product behavior:
   - preserve failed model attempts for evidence
   - make two-stage finalization prompt an exact JSON copying task
   - make ReAct tool prompts explicit tool-call requests
4. Run local unit and local compatible provider acceptance.
5. Run live OpenRouter DeepSeek V4 Flash acceptance gates with secrets supplied only through process env/stdin.
6. Use disposable SQLite databases for live gates that seed provider rows.
7. Scan for accidental secret persistence.
8. Commit the slice.

## Test Matrix

- RED: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/red.txt`
- Unit: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/unit.txt`
- Local compatible provider: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/local-compatible.txt`
- Ruff: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/ruff.txt`
- Customer assistant live: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/customer-assistant-live-react.txt`
- Runtime Lab live Chatflow SOP: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/runtime-lab-live-chatflow-llm-sop.txt`
- Runtime Lab OpenRouter full chain: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/runtime-lab-openrouter-full-chain.txt`
- Product chat live paths: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/openrouter-product-chat-paths.txt`
- OpenRouter provider/tool-call contract: `artifacts/slices/135-openrouter-deepseek-v4-flash-live-gate/135.1/openrouter-llm-tool-call.txt`
