# Workflow/Chatflow Coze Alignment Audit

Date: 2026-06-02

## Verdict

The current implementation now has a tested six-node runtime matrix for workflow and chatflow MVP paths. It is not a complete pixel-level or behavior-level Coze replica.

The strongest verified areas are:

- Existing six node types can be created, saved, rendered on canvas, run as a full chain, and run individually from the selected-node drawer.
- Workflow and chatflow full-chain runs both exercised real Knowledge retrieval and real LLM provider calls.
- START variables, test-run input labels, single-node variable fixtures, and `topK` runtime behavior are now covered by tests.

The weakest areas are:

- API_CALL is still mock runtime.
- LLM panel is a partial Coze shell, not the full Coze node configuration surface.
- Condition builder is expression/edge-condition based, not a full multi-row Coze condition UI builder.
- Variable reference scope is functional and graph-aware, but not proven equivalent to every Coze scope/type rule.
- Official Coze live page visual control could not be completed in this pass: two browser attempts timed out while loading the Coze URL. Local Hify UAT screenshots were captured; no fresh Coze screenshot is claimed here.

## Node Panel Parity

| Node | Current Hify status | Coze parity assessment |
| --- | --- | --- |
| START | Shows fixed card, output variable chips, tooltip truncation behavior from prior work, single-node run inputs now include declared variables. | Partial. Variable display is close for common chips, but full Coze variable management semantics need deeper comparison. |
| LLM | Has model shell, single mode, prompt fields, Knowledge resource context, output parameters, selected-node run, real default LLM profile. | Partial. Missing full Coze model parameter matrix, visual understanding, batch mode, continuation, exception handling, full skill/tool/subworkflow runtime. |
| CONDITION | Has expression field, output parameter, edge condition routing, multi-branch backend support through multiple outgoing edges. | Partial. Not a full Coze multi-condition visual builder; complex condition row UX needs dedicated slice. |
| KNOWLEDGE | Has KB ID, query, `topK`, output parameter, real facade retrieval. `topK` now runtime-backed. | Partial. Missing full KB selector, rerank/citation/score controls, rich source preview. |
| API_CALL | Has method, endpoint, output parameter, variable interpolation. | Low parity. Runtime is still `API mock`, no real HTTP headers/body/auth/error mapping. |
| END | Has response content and output variable rendering. | Partial. Adequate for MVP output handoff; not full Coze response formatting/tooling. |

## Lifecycle Parity

| Step | Workflow | Chatflow | Status |
| --- | --- | --- | --- |
| List/create/open canvas | Implemented and tested in earlier slices. | Implemented and tested in earlier slices. | Basic parity |
| Canvas edit/save | Nodes/edges/config persist; positions persist. | Same shared canvas path. | Basic parity |
| Full-flow run | Six-node e2e passed. | Six-node e2e passed. | Runtime-backed MVP |
| Selected-node run | Six node types verified in workflow e2e; backend supports both routers. | LLM profile previously verified for chatflow; six-node full run verified. | Mostly covered; per-node chatflow drawer matrix still needs explicit e2e if required. |
| Publish/open/observe shell | Shell implemented in 011.9. | Shell implemented for shared surface. | Shell only |
| Conversation settings | Opening message and guide questions are present and previously wired into run preview. | Present in browser UAT. | Partial, not full Coze parity |

## Interaction Parity

| Interaction | Current status | Risk |
| --- | --- | --- |
| Add/remove input variables | Implemented with typed rows and tested in earlier slices. | Need broader Coze comparison for all row affordances and validation messages. |
| Add/remove output variables | Implemented with typed rows and tested in earlier slices. | Multi-output runtime mapping still uses simple executor outputs per node type. |
| Variable reference picker | Graph-aware upstream/start/global catalog exists; chatflow sys variables exist. | Coze's full scope/type filtering and nested object path behavior are not fully replicated. |
| Reference effect | `{{node.variable}}` and `{{start.variable}}` render through `ExecutionContext`; six-node tests verify references across START, KB, LLM, API, END. | Complex array/object formatting and invalid reference UX need more tests. |
| Node dragging | Previously fixed with VueFlow move persistence. | Needs another browser regression if current Coze-like layout changes continue. |
| Bottom toolbar | Visible mode toggle icon, add node, run, zoom controls present. | Local UAT screenshot shows some nodes partially off-screen in dense matrix layout; auto-fit/overview behavior needs polish. |

## Follow-up Slice Candidates

1. `011.13-condition-builder-parity`: Coze-like multi-condition row builder, edge condition synchronization, red/green branch UAT.
2. `011.14-api-call-real-runtime`: real HTTP method/header/body/auth/timeout/error/output mapping.
3. `011.15-variable-scope-parity`: variable picker type filtering, nested refs, invalid reference diagnostics, chatflow per-node matrix.
4. `012.x-chatflow-node-matrix`: selected-node drawer e2e for every node type in chatflow mode, not only full-chain run.
5. `015.x-extra-coze-nodes`: CODE/TEXT_PROCESS/JSON_PARSE/VARIABLE/INTENT/MESSAGE/HUMAN_INPUT nodes from spec015.
