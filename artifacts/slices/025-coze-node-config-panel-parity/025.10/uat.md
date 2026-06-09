# 025.10 Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5176`

## Result

PASS. Browser automation created real Workflow/Chatflow canvases and verified the structured node panels.

Verified panels:

- `JSON_PARSE`: basic panel renders `字段映射` as row editor with `输出变量` / `JSONPath` / `变量类型`; no raw textarea exists inside `json-field-mapping-editor`.
- `VARIABLE_AGGREGATION`: basic panel renders `来源列表` as rows, and reference values render as variable chips.
- `VARIABLE_ASSIGN`: basic panel renders target scope, target variable, write mode, and source value in `variable-assignment-editor`; source reference renders as a variable chip.
- `HUMAN_INPUT`: basic panel renders `输入结构` as schema rows with field name, type, required switch, and description.

Screenshots:

- `e2e-transform-nodes.png`
- `e2e-variable-aggregation-assignment.png`
- `e2e-human-input-schema.png`

Runtime UAT support:

- Transform workflow ran through `CODE -> TEXT_PROCESS -> JSON_PARSE -> END`.
- Variable workflow ran through `VARIABLE_AGGREGATION -> VARIABLE_ASSIGN -> END`.
- Chatflow ran through `MESSAGE -> QUESTION -> HUMAN_INPUT -> END` with resume payload.

Full machine-readable details are in `uat-browser.json`.
