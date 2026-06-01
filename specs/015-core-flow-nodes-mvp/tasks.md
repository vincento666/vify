# Tasks 015: Core Flow Nodes MVP

## 015.1 Data transform nodes

- [ ] RED: CODE/TEXT_PROCESS/JSON_PARSE tests fail.
- [ ] Implement node metadata and config forms.
- [ ] Implement deterministic executors.
- [ ] Add JSON_PARSE strict parse and mapped-field output.
- [ ] Gates pass.

## 015.2 Variable aggregation and assignment

- [ ] RED: variable aggregation and assignment tests fail.
- [ ] Implement VARIABLE_AGGREGATION metadata, config form, and deterministic aggregator executor for Coze `变量聚合` semantics.
- [ ] Implement scope selector and VARIABLE_ASSIGN executor separately from aggregation.
- [ ] Implement current supported mock/persistent scopes.
- [ ] Keep JSON parsing out of VARIABLE_ASSIGN.
- [ ] Verify the add-node palette labels aggregation as `变量聚合` and does not make unsupported Coze entries runnable.
- [ ] Gates pass.

## 015.3 LLM intent branch

- [ ] RED: intent branch test fails.
- [ ] Implement intent node dynamic ports.
- [ ] Implement fake/LLM intent classifier adapter.
- [ ] Gates pass.

## 015.4 Chat message/question/input

- [ ] RED: message/question/input pause/resume tests fail.
- [ ] Implement MESSAGE node.
- [ ] Implement QUESTION node with wait/resume contract.
- [ ] Implement HUMAN_INPUT node for explicit manual pause/input.
- [ ] Share content editor UI while preserving separate runtime events.
- [ ] Gates pass.

## 015.5 Smart info collection

- [ ] RED: multi-turn slot collection test fails.
- [ ] Implement slot schema, extraction, state merge, missing-field prompt, max rounds.
- [ ] Implement chat history awareness option.
- [ ] Default to structured output; support advanced direct variable writes through assignment path.
- [ ] Gates pass.
