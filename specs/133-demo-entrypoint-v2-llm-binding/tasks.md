# 133 Tasks

- [x] RED: Runtime Lab and Customer Assistant entrypoints fail provider-backed
      runtime-v2 SOP LLM assertions before resolver wiring.
- [x] GREEN: Runtime Lab runtime-v2 SOP service uses provider-backed completer
      resolver with existing preferred agent name.
- [x] GREEN: Customer Assistant runtime-v2 SOP adapter uses provider-backed
      completer resolver with existing preferred agent name.
- [x] Preserve no-provider deterministic mock behavior.
- [x] Run focused entrypoint tests.
- [x] Run related Runtime Lab and Customer Assistant regressions.
- [x] Run Ruff for touched files.
- [ ] Commit focused feature point.

## Evidence

- RED: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/red.txt`
- Focused entrypoints: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/focused.txt`
- Customer Assistant SOP adapter regression: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/customer-assistant-sop-adapter.txt`
- Runtime Lab Chatflow SOP e2e regression: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/runtime-lab-chatflow-sop-e2e.txt`
- Ruff: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/ruff.txt`
- Browser UAT: `artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/uat.md`
