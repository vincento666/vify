# Spec 004: Agent Management

## Goal

Replicate Agent creation/configuration, model binding, knowledge/workflow IDs,
and MCP tool binding.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 004.1 Agent CRUD | User can create/list/detail/update/delete agents | RED: route contract fails; Unit: schema validation; Integration: DB CRUD; E2E: agent page smoke; UAT: create/edit/delete agent |
| 004.2 Model validation | Agent create/update rejects missing or disabled model config | RED: negative tests fail; Unit: service rule; Integration: provider facade; E2E: form error; UAT: invalid model rejected |
| 004.3 Tool binding | User can replace an agent's MCP tool bindings | RED: binding tests fail; Unit: duplicate filtering; Integration: join table; E2E: tool binding UI; UAT: selected tools persist |
| 004.4 Knowledge/workflow binding | Agent can store optional `knowledge_base_id` and `workflow_id` | RED: schema-field tests fail; Unit: nullable behavior; Integration: DB columns; E2E: form values persist; UAT: bindings visible |

## Compatibility Rules

- Agent list includes tool count.
- `temperature`, `max_tokens`, and `max_context_turns` validation matches current
  Java constraints.
- Delete remains logical delete where the source uses MyBatis-Plus logical delete.
