# Tasks 015: Core Flow Nodes MVP

## 015.1 Data transform nodes

- [x] RED: CODE/TEXT_PROCESS/JSON_PARSE tests fail.
- [x] Implement node metadata and config forms.
- [x] Implement deterministic executors.
- [x] Add JSON_PARSE strict parse and mapped-field output.
- [x] Gates pass.

## 015.2 Variable aggregation and assignment

- [x] RED: variable aggregation and assignment tests fail.
- [x] Implement VARIABLE_AGGREGATION metadata, config form, and deterministic aggregator executor for Coze `变量聚合` semantics.
- [x] Implement scope selector and VARIABLE_ASSIGN executor separately from aggregation.
- [x] Implement current supported mock/persistent scopes.
- [x] Keep JSON parsing out of VARIABLE_ASSIGN.
- [x] Verify the add-node palette labels aggregation as `变量聚合` and does not make unsupported Coze entries runnable.
- [x] Gates pass.

## 015.3 LLM intent branch

- [x] RED: intent branch test fails.
- [x] Implement intent node dynamic ports.
- [x] Implement fake/LLM intent classifier adapter.
- [x] Gates pass.

## 015.4 Chat message/question/input

- [x] RED: message/question/input pause/resume and streaming event tests fail.
- [x] Implement MESSAGE node.
- [x] Implement MESSAGE streaming config: inherit/enabled/disabled, stream target, fallback aggregation.
- [x] Emit `message_delta`, `message_done`, `llm_delta`, and `stream_error` events where supported while keeping downstream outputs final-only.
- [x] Implement QUESTION node with wait/resume contract.
- [x] Implement HUMAN_INPUT node for explicit manual pause/input.
- [x] Share content editor UI while preserving separate runtime events.
- [x] Gates pass.

## 015.5 Smart info collection

- [x] RED: multi-turn slot collection test fails.
- [x] Implement slot schema, extraction, state merge, missing-field prompt, max rounds.
- [x] Implement chat history awareness option.
- [x] Implement optional streaming follow-up output for incomplete INFORMATION_COLLECTION.
- [x] Default to structured output; support advanced direct variable writes through assignment path.
- [x] Gates pass.

## 015.6 Core node parity regression

- [x] RED: JSON_PARSE bracket array JSONPath test fails with empty mapped fields for `$.items[0].sku`.
- [x] Add JSON_PARSE bracket path support while preserving dot-separated array index support.
- [x] Re-run core node parity gates for CODE, TEXT_PROCESS, JSON_PARSE, CONDITION/selector, INTENT_RECOGNITION, INFORMATION_COLLECTION, EXECUTE_WORKFLOW, and API_CALL/resource flows.
- [x] Evidence: `artifacts/slices/083-workflow-chatflow-canvas-node-parity/`.
- [x] Gates pass.
