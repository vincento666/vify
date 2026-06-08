# Browser UAT

- URL: generated workflow canvas from `workflow-variable-aggregation-official.mjs`.
- Viewport: 1440x900.
- Scenario: open a workflow containing `变量聚合`, inspect the node card and config panel.
- Result: passed.

Verified:
- The card shows grouped outputs and no generic `未配置输入`.
- The panel has `聚合策略`, `变量分组`, and read-only `输出`.
- Group header name renders as normal text; clicking enters edit mode; Enter confirms.
- Group variables use a candidate row and no `新增变量` button.
- Output rows are derived from groups and are not editable output-parameter forms.

Screenshot:
- `artifacts/slices/083-variable-aggregation-official-alignment/screenshots/workflow-variable-aggregation-official.png`
- `artifacts/slices/083-variable-aggregation-official-alignment/screenshots/workflow-variable-aggregation-official-latest.png`
