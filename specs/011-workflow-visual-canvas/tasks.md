# Tasks 011: Workflow Visual Canvas

## 011.1 Workflow tab shell

- [x] RED: route/list UI test fails.
- [x] Implement Workflow/Chatflow tabs in workflow module shell.
- [x] Preserve existing workflow list behavior.
- [x] Gates pass.

## 011.2 Canvas graph editor

- [x] RED: canvas save/reopen test fails.
- [x] Add `@vue-flow/core`.
- [x] Implement Coze-like custom node cards, ports, hover/selected/run states, and edge labels.
- [x] Implement default START/END graph.
- [x] Implement add, drag, connect, delete, save, reopen.
- [x] Gates pass.

## 011.3 Node config panel

- [x] RED: node config persistence test fails.
- [x] Implement node metadata registry.
- [x] Implement unified config panel for START, LLM, CONDITION, KNOWLEDGE, API_CALL, END.
- [x] Gates pass.

## 011.4 Variable reference selector

- [x] RED: variable selector test fails.
- [x] Implement graph-aware variable catalog builder limited to connected upstream outputs plus START/global variables.
- [x] Implement Coze-like grouped/searchable variable selector for node input/config fields.
- [x] Preserve `{{node.variable}}` template syntax in saved config.
- [x] Gates pass.

## 011.5 Validate and test run

- [x] RED: test run UI fails.
- [x] Implement graph validator.
- [x] Add test input panel and run result mapping.
- [x] Gates pass.

## 011.6 Publish/open/observe shell

- [x] RED: publish guard fails.
- [x] Implement publish guard and publish modal shell.
- [x] Implement open API and observe tab placeholders with business fields.
- [x] Gates pass.
