# 124 Product Reference Benchmark

Date: 2026-06-09

## Why This Slice Exists

Previous gates proved the current Hify implementation did not regress at the automated test level, but that is not enough for the workflow/chatflow polish goal. This slice adds product-reference evidence from Coze documentation, Coze Studio official material, AgentArts/HiAgent references, and current Hify screenshots.

## Reference Sources

- Coze workflow/chatflow docs: https://docs.coze.com/guides/workflow_and_chatflow
- Coze condition node docs: https://docs.coze.com/guides/condition_node
- Coze variable merge node docs: https://docs.coze.com/guides/variable_merge_node
- Coze variable assign node docs: https://docs.coze.com/guides/variable_assign_node
- Coze question node docs: https://docs.coze.com/guides/question_node
- Coze node catalog pages captured from the official docs sidebar:
  - `start_end_node`, `llm_node`, `variable_node`, `message_node`, `input_node`, `json_deserialization_node`, `knowledge_node`, `http_node`
- Coze Studio official backend node extension wiki: https://github.com/coze-dev/coze-studio/wiki/11.-Add-new-workflow-node-types-(backend)
- AgentArts variable assignment manual URL provided by the user: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0084.html

## Browser Evidence

Coze cloud workspace access:

- Tried `https://www.coze.com/space`.
- Result: redirected to `https://www.coze.com/sign?redirect=...`.
- Evidence screenshot: `artifacts/research/workflow-chatflow-product-reference-2026-06-09/screenshots/coze-space-entry.png`
- Interpretation: actual Coze online canvas cannot be accessed in this environment without user login. Do not claim pixel-level Coze canvas verification unless a logged-in workspace is available.

Coze official docs screenshots:

- `screenshots/coze-workflow-chatflow-doc-fixed.png`
- `screenshots/coze-condition-node.png`
- `screenshots/coze-variable-merge-node.png`
- `screenshots/coze-variable-assign-node.png`
- `screenshots/coze-question-node.png`
- plus additional captured node docs under the same screenshots directory.

AgentArts direct browser access:

- Tried the official variable assignment manual URL.
- Browser result: Tencent Cloud EdgeOne security verification page.
- Evidence screenshot: `screenshots/agentarts-variable-assignment.png`
- User-provided screenshots remain valid visual references, but official live page screenshot is blocked by security verification in this environment.

Current Hify screenshots:

- `screenshots/hify-condition-panel.png`
- `screenshots/hify-variable-aggregation-panel.png`
- `screenshots/hify-variable-assign-panel.png`

## Product Facts Captured

- Coze separates workflow and chatflow: workflow is for functional task execution, while chatflow is a specialized workflow for chat scenarios, bound to a conversation and able to read chat history.
- Coze condition node is an if/else branching node; branches can have multiple conditions, AND/OR logic, multiple conditional branches, and draggable branch priority.
- Coze variable merge node merges outputs from multiple branch workflows, mainly using "return the first non-empty value in each group"; variables in a group must share the same type.
- Coze variable assign node is for modifying/storing variable values, not for generic output formatting. Its panel model is centered on selecting a parameter name and assigning a value.
- Coze question node asks designated questions and waits for user response; it supports direct reply and option-based reply modes.

## Hify Gap Notes

- `VARIABLE_ASSIGN` currently still uses a generic `输入` plus `输出` shell. The visible `输出格式/输出变量` controls do not match the variable-assignment mental model from Coze/AgentArts.
- `VARIABLE_AGGREGATION` is closer to Coze, but must continue to align with:
  - group name as a header, not a normal variable item;
  - click-to-edit group name;
  - same-type variables in each group;
  - auto-append empty source row after selecting a source variable;
  - output derived from merge group definitions.
- `CONDITION` is close to the Coze selector model, but still needs strict product verification for:
  - branch-name editing;
  - nested/secondary condition rows;
  - comparison operator menu;
  - variable reference picker behavior inside left/right operands;
  - branch endpoint/card alignment.
- Hify right config panel can intercept canvas node clicks when open. That is acceptable only if the intended UX requires closing the panel first; otherwise it should be checked in a dedicated interaction slice.

## Next Implementation Order

1. Fix `VARIABLE_ASSIGN` panel semantics first because it visibly contradicts Coze/AgentArts: remove generic output-format shell, center the form on target variable plus value assignment, and keep runtime output contract only if needed for downstream references.
2. Finish `VARIABLE_AGGREGATION` UI parity: group header editing, auto-row append, grouped output, and source row behavior.
3. Re-audit `CONDITION` against Coze screenshots: branch editing, operator options, two-column row layout, nested conditions, and card endpoint geometry.
4. Continue node-by-node reference matrix for JSON parse, intent recognition, API/HTTP, knowledge, plugin/tool, agent/subworkflow, message/question/info collection.

## Verdict

PASS for product-reference evidence collection. Not a product-parity pass yet. The next slices must use these reference screenshots and official pages as entry criteria before automated gates.
