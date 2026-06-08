# 084 Workflow/Chatflow Node Catalog Audit

References:
- Coze docs: https://www.coze.com/open/docs/guides/workflow_and_chatflow (public page currently sparse).
- AgentArts workflow intro: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0041.html lists node families.
- AgentArts task/chat workflow difference: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0042.html states task workflows do not support input/message/question/Q&A/object-extract/Agent nodes.
- AgentArts variable aggregation: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0085.html confirms one Group header maps to one output and only first-non-empty strategy.

Decision:
- Keep node type runtime support backward compatible.
- Filter create palette by mode: task workflow hides conversation-only and Agent nodes; chatflow keeps conversation-oriented nodes.
