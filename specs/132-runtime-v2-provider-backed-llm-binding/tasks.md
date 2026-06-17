# 132 Tasks

- [x] RED: provider-backed runtime-v2 LLM API tests fail before binding exists.
- [x] GREEN: expose/reuse WorkflowService provider-backed completer for runtime v2.
- [x] GREEN: runtime-v2 execution resolves completer by owner id.
- [x] GREEN: workflow/chatflow routers and background completion inject resolver.
- [x] Preserve deterministic mock behavior when no live provider-backed agent exists.
- [x] Run focused integration gates.
- [x] Run legacy LLM and runtime-v2 regressions.
- [x] Run Ruff for touched files.
- [ ] Commit focused feature point.

## Evidence

- RED: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/red.txt`
- Focused integration: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/focused.txt`
- Runtime-v2 regression: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/runtime-v2-regression.txt`
- Legacy LLM regression: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/legacy-llm-regression.txt`
- API integration: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/integration.txt`
- Ruff: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/ruff.txt`
- Browser UAT: `artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/uat.md`
