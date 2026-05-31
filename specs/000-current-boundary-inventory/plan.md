# Plan 000: Current Boundary Inventory

## Approach

Use the inspected Java repository as a read-only baseline. Extract route,
schema, module, and mock-behavior facts into this spec before implementing any
Python code.

## Inventory Sources

- Java controllers for route matrix.
- `hify-app/src/main/resources/db/schema.sql`
- `hify-app/src/main/resources/db/schema-h2.sql`
- `KnowledgeServiceImpl` for mock RAG.
- `MockProviderAdapter` and `ChatServiceImpl` for mock LLM/tool behavior.
- `McpServiceImpl` for MCP client expectations.

## Deliverables

- Route matrix in this spec or linked notes.
- Target Alembic table list.
- Mock behavior matrix.
- Feature spec order and slice split.

## Exit Criteria

`001-backend-foundation` may start only after this spec records that the target
database baseline must be the H2/MySQL superset.
