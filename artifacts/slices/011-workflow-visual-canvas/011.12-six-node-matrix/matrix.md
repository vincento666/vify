# 011.12 Six-node Matrix

Date: 2026-06-02

## Scope

Current runtime-backed node types:

1. START
2. CONDITION
3. KNOWLEDGE
4. LLM
5. API_CALL
6. END

## Matrix

| Node | Config fields verified | Single-node run | Full-chain role | Evidence |
| --- | --- | --- | --- | --- |
| START | `outputVariables`, variable chips, fixed input labels | Returns provided input without downstream execution | Seeds `USER_INPUT` / `sys.query` | `tests/unit/workflow/test_six_node_matrix.py`, `frontend/e2e/workflow-six-node-matrix.mjs` |
| CONDITION | `expression`, `outputVariable`, edge condition value | Renders `{{start.USER_INPUT}}` to `route` | Routes branch value `kb` to Knowledge | `tests/unit/workflow/test_six_node_matrix.py`, `tests/integration/workflow/test_six_node_matrix.py` |
| KNOWLEDGE | `knowledgeBaseId`, `topK`, `query`, `outputVariable` | Retrieves real KB chunks; `topK=2` is passed to facade | Supplies retrieved context to LLM | `red.txt`, `unit.txt`, `integration.txt`, `e2e.txt` |
| LLM | model shell, prompt, output variable, current real-provider profile | Calls default live LLM agent; rejects mock-provider profile | Produces marker consumed by API_CALL | `frontend/e2e/workflow-six-node-matrix.mjs`, backend logs show OpenRouter 200 |
| API_CALL | `method`, `endpoint`, `outputVariable` | Renders endpoint variable and returns existing mock executor output | Consumes LLM marker in URL | `tests/unit/workflow/test_six_node_matrix.py`, `e2e.txt` |
| END | `output`, `outputVariable`, input references | Renders `{{api.response}}` | Final workflow/chatflow response | `tests/unit/workflow/test_six_node_matrix.py`, `frontend/e2e/workflow-six-node-matrix.mjs` |

## Gate Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| RED | PASS | `red.txt`: Knowledge `topK` failed as expected; `frontend-red.txt`: START node fixture inputs failed as expected; `llm-retry-red.txt`; `llm-proxy-red.txt` |
| Unit | PASS | `unit.txt`: 5 backend tests passed; `frontend-unit.txt`: 3 frontend fixture tests passed |
| Integration/Contract | PASS | `integration.txt`: 4 workflow endpoint tests passed |
| E2E | PASS | `e2e.txt`: workflow/chatflow six-node matrix passed |
| Browser UAT | PASS with visual caveats | `screenshots/browser-uat-workflow-673.png`, `screenshots/browser-uat-chatflow-674.png` |
| Docs | PASS | This matrix and `audit.md` |

## Runtime Notes

- Workflow e2e used workflow `673`: `Workflow Six Node Matrix SN_1780359278280`.
- Chatflow e2e used chatflow `674`: `Chatflow Six Node Matrix SN_1780359278280`.
- LLM calls used the configured real OpenRouter profile. The client now retries transient `httpx.TransportError` and disables inherited system proxy settings with `trust_env=False`, because browser e2e exposed repeated TLS EOF through the local proxy.
- API_CALL remains an explicit project mock executor: `API mock: METHOD URL`. This is not full Coze parity.
