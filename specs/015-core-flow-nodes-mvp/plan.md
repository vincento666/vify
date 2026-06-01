# Plan 015: Core Flow Nodes MVP

## Architecture

- Reuse 011/012 canvas node registry and right-panel form framework.
- Add node runtime through small executor classes and profile adapters.
- Keep Chatflow-only behavior behind Chatflow runtime profile:
  - message emit
  - wait/resume events
  - chat history awareness
  - slot collection state
- Keep JSON_PARSE as deterministic data transform; keep VARIABLE_ASSIGN as variable-scope write.
- Add VARIABLE_AGGREGATION as the Coze-aligned `变量聚合` node. It normalizes/merges upstream values and branch outputs; it must not be conflated with scope assignment.
- Keep live Coze palette entries disabled until runtime-backed: plugin, workflow/subflow, loop, batch, async, database CRUD, and knowledge write/search beyond existing retrieval.
- Use fake LLM adapters for RED/green tests first, then wire provider-backed LLM where provider contracts exist.
- Reuse one content editor component for MESSAGE and QUESTION, but keep node types and runtime events separate.
- Add a profile-level event model for Chatflow nodes instead of embedding message/interrupt branching into every executor.

## Runtime Notes

- INFORMATION_COLLECTION needs checkpoint-like state, but not full Task Stack.
- QUESTION and HUMAN_INPUT require single-flow interrupt/resume, not cross-flow task switching.
- INTENT_RECOGNITION uses dynamic branch ports like CONDITION, but branch selection comes from LLM semantic output.
- MESSAGE maps to an output/message event and continues.
- QUESTION/HUMAN_INPUT/unfinished INFORMATION_COLLECTION map to interrupt events and require resume.
- INFO collection defaults to structured output; direct scope writes are advanced config and should reuse assignment infrastructure.
- Palette labels should use user-facing Coze-aligned names where helpful: `代码`, `选择器`, `意图识别`, `变量聚合`, while preserving explicit internal node type names in tests and API payloads.

## Slice Order

015.1 -> 015.2 -> 015.3 -> 015.4 -> 015.5
