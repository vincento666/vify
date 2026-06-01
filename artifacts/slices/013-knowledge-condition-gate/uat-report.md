# Spec013 Knowledge + Condition Canvas Gate

Date: 2026-06-01

## Scope

- Workflow and chatflow canvas runs preserve condition edge routing after load/save.
- `CONDITION` nodes can route to a `KNOWLEDGE` node and to a default branch.
- `KNOWLEDGE` nodes use `KnowledgeFacade` retrieval in direct canvas runs.
- No direct canvas run may silently return `Knowledge mock:`.
- Chatflow variables such as `{{start.sys.query}}` render correctly.

## Gate Results

| Gate | Command / Method | Result |
| --- | --- | --- |
| RED/Unit | `uv run pytest tests/unit/workflow/test_service_knowledge_condition.py -q` | Passed after implementation, covers real KnowledgeFacade injection and no-facade rejection |
| Workflow unit suite | `uv run pytest tests/unit/workflow -q` | Passed, 15 tests |
| Python lint | `uv run ruff check app/modules/workflow/domain/service.py app/modules/workflow/web/router.py app/modules/workflow/domain/context.py tests/unit/workflow/test_service_knowledge_condition.py tests/unit/workflow/test_execution_context.py` | Passed |
| Python typing | `uv run mypy app/modules/workflow/domain/service.py app/modules/workflow/domain/context.py` | Passed |
| API smoke | Create KB + upload document + run condition->knowledge workflow and default branch | Passed, real KB token returned, no `Knowledge mock:` |
| Frontend unit | `npm --prefix frontend run test:unit` | Passed, 18 files / 34 tests |
| Frontend build | `npm --prefix frontend run build` | Passed |
| Browser e2e | `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-knowledge-condition-run.mjs` | Passed |

## Browser Evidence

- Workflow KB-hit screenshot: `artifacts/slices/013-knowledge-condition-gate/workflow-kc-hit.png`
- Workflow default-branch screenshot: `artifacts/slices/013-knowledge-condition-gate/workflow-kc-default.png`
- Chatflow KB-hit screenshot: `artifacts/slices/013-knowledge-condition-gate/chatflow-kc-hit.png`
- Chatflow default-branch screenshot: `artifacts/slices/013-knowledge-condition-gate/chatflow-kc-default.png`

The Codex in-app Browser control tool was still not exposed in this session after tool discovery, so browser UAT used Playwright against the same running local frontend/backend.
