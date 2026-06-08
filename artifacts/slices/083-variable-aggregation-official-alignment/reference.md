# Reference Notes

Official / primary references used:

- AgentArts variable aggregation manual: `https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0042.html`
  - Variable aggregation combines outputs from multiple branch nodes.
  - The strategy is to return the first non-empty value in each group.
  - Variables in the same group should be the same type; each group becomes an output.
- Local Coze Studio source:
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/nodes-v2/variable-merge/components/variable-merge-form/index.tsx`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/nodes-v2/variable-merge/components/merge-groups-field/index.tsx`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/nodes-v2/variable-merge/components/group-variables/index.tsx`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/nodes-v2/variable-merge/components/group-header/index.tsx`

Implementation decisions:

- Hify keeps the legacy `sources` JSON in advanced compatibility only.
- The main panel uses `groups` / `mergeGroups` style data.
- Group names render read-first; clicking the header enters edit mode.
- Group variables append through the candidate value field; no manual add-variable button.
- Outputs are read-only summaries derived from groups, not a generic editable output form.
