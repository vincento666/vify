# Plan 004: Agent Management

## Architecture

Use provider API facade for model config validation. Agent service owns
transaction boundaries for agent and agent_tool writes.

## Testing Notes

- Contract tests must verify current field names.
- Integration tests must prove tool binding is full replacement, not merge.
- UAT must use the real frontend Agent page.

## Slice Order

004.1 -> 004.2 -> 004.3 -> 004.4
