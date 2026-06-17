# 131 Runtime V2 LLM Node Core Support

## Goal

Let Workflow runtime v2 execute a basic LLM node through the existing workflow
LLM node executor so the productized MVP no longer treats LLM nodes as an
unsupported runtime-v2 graph.

## Acceptance Criteria

- RED proves `/runs-v2` rejects an LLM node before the slice.
- Runtime v2 compatibility includes `LLM` while still rejecting unsupported
  nodes such as `TOOL_CALL`.
- Runtime v2 LLM execution records node started/completed events and node-run
  outputs.
- Without a configured LLM provider/completer, the node falls back to the same
  deterministic mock output already used by the legacy engine.
- Focused runtime-v2 tests and Ruff pass.

## Non-goals

- Do not add live provider credentials or make network calls.
- Do not implement LLM tool-calling in runtime v2.
- Do not change frontend layout or browser behavior.

## Evidence

Evidence lives under
`artifacts/slices/131-runtime-v2-llm-node-core-support/131.1/`.
