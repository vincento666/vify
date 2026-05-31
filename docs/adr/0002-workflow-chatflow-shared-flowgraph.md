# Workflow and Chatflow share a FlowGraph runtime

Accepted. Workflow and Chatflow will remain separate product resources with separate list/create entries, but they share the same graph language, node catalog, canvas components, persistence shape, and executor path. Internally they are stored as shared flow records distinguished by `flow_type`; Chatflow is a conversational runtime profile on top of the shared flow model, adding system variables, conversation/user/channel variable scopes, message history access, and future interrupt/resume behavior instead of creating a second incompatible workflow engine.

## Considered Options

- Separate Workflow and Chatflow engines: clearer isolation, but duplicates node behavior and makes shared canvas work expensive.
- One mixed flow list with filters: simpler UI, but conflicts with product language and hides Chatflow-specific variables.
- Shared FlowGraph with separate resource entries: chosen because it matches the Coze/HiAgent product shape while keeping backend/runtime reuse high.

## Consequences

The API and UI must expose Workflow List and Chatflow List as separate user-facing entries. Internally, graph, node, edge, validation, run evidence, and most canvas code should be reusable through `flow_type` separation and runtime profiles. Dify-style cross-flow task switching stays out of the first replica and will be researched as a future Task Stack capability.
