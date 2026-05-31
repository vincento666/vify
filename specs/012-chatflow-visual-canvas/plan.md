# Plan 012: Chatflow Visual Canvas

## Architecture

- Reuse Workflow canvas components from spec 011.
- Add first-class `flow_type` to API/UI/backend resources with values `WORKFLOW` and `CHATFLOW`.
- Keep graph nodes/edges/run tables shared.
- Filter `/api/v1/workflows` to `flow_type=WORKFLOW` resources by default.
- Add `/api/v1/chatflows` facade routes for Chatflow list/create/detail/update/delete/run while reusing shared service internals.
- Keep type-specific behavior behind runtime profile adapters instead of branching throughout the executor.
- Add Chatflow system variable catalog and variable reference selector.
- Map Chatflow test message to shared executor input:
  - `sys.query` and compatibility `userMessage`.
  - `sys.conversation_id`, `sys.conversation_name`, `sys.user_id`, `sys.channel`, `sys.now`, `sys.message_id`, `sys.round`, `sys.files`.
- Store baseline variable definitions in graph config until durable variable storage is specified.

## Runtime Notes

- Shared executor stays deterministic and synchronous in replica phase.
- Chatflow profile is a wrapper around run input/output and variable/message behavior, not a new executor.
- Conversation/message persistence can reuse current chat tables only for test evidence; channel adapters and long-lived scoped variables are later specs.

## UI Shape

- Workflow module tabs: Workflow, Chatflow.
- Chatflow list mirrors Workflow list but uses Chatflow terms and create button.
- Chatflow canvas left panel includes node palette plus variable scopes.
- Test panel is message-shaped, not generic JSON-shaped.

## Slice Order

012.1 -> 012.2 -> 012.3 -> 012.4 -> 012.5
