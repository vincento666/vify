# Official Reference Mapping

Generated for Spec 194 phase 1 productionization.

## Sources

Coze official docs:

- https://www.coze.cn/open/docs/guides/workflow
- https://www.coze.cn/open/docs/guides/use_workflow
- https://www.coze.cn/open/docs/guides/code_node
- https://www.coze.cn/open/docs/guides/http_node
- https://www.coze.cn/open/docs/guides/plugin_node
- https://www.coze.cn/open/docs/guides/condition_node
- https://www.coze.cn/open/docs/guides/variable
- https://www.coze.cn/open/docs/guides/add_variables_in_app
- https://www.coze.cn/open/docs/guides/variable_assign_node
- https://www.coze.cn/open/docs/guides/variable_merge_node
- https://www.coze.cn/open/docs/guides/start_end_node
- https://www.coze.cn/open/docs/guides/question_node
- https://www.coze.cn/open/docs/guides/message_node
- https://www.coze.cn/open/docs/guides/preview_debug
- https://www.coze.cn/open/docs/guides/view_running_log
- https://www.coze.cn/open/docs/guides/collaborate_workflow
- https://www.coze.cn/open/docs/guides/run_app_as_api
- https://www.coze.cn/open/docs/guides/import_and_export_workflow

Coze Studio official repository/wiki:

- https://github.com/coze-dev/coze-studio/wiki/11.-Add-new-workflow-node-types-%28backend%29
- https://github.com/coze-dev/coze-studio/wiki/10.-Add-new-workflow-node-types-%28frontend%29
- https://github.com/coze-dev/coze-studio/wiki/6.-API-Reference
- https://github.com/coze-dev/coze-studio/wiki/4.-Plugin-Configuration
- https://github.com/coze-dev/coze-studio/wiki/3.-Model-configuration

HiAgent / Volcengine official docs:

- https://www.volcengine.com/product/hiagent
- https://www.volcengine.com/docs/86760/1874948
- https://www.volcengine.com/docs/86760/2479183?lang=zh
- https://www.volcengine.com/docs/86760/2479180
- https://www.volcengine.com/docs/86760/2407044
- https://www.volcengine.com/docs/86760/2283617
- https://www.volcengine.com/docs/86760/2280963
- https://www.volcengine.com/docs/86760/2280864
- https://www.volcengine.com/docs/86760/2306535?lang=en
- https://www.volcengine.com/docs/86760/2277084

## Phase 1 Mapping

| Hify area | Reference semantics | Phase 1 requirement |
| --- | --- | --- |
| Error handling | Coze node-level exception handling and branch/fallback behavior; HiAgent observability for failures | `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`, `EXECUTE_WORKFLOW`, `AGENT_CALL` support `fail`, `continue`, `branch`; missing error outlet blocks run/publish |
| Runtime/debug trace | Coze preview/debug and running log/Trace; HiAgent span/token/latency observability | runtime v2 records run/node status, events, inputs, outputs, errors, elapsed time, variable snapshots, external-call evidence |
| Variables | Coze system/user/app variables, start/end nodes, variable assign/merge; HiAgent template/global vars | system variables read-only, scoped variables typed/required/defaulted, illegal refs reported before run/publish |
| API/HTTP | Coze HTTP node retry/status/body/header/auth semantics; HiAgent REST/OpenAPI auth scope | direct `API_CALL` supports auth, templates, status policy, retry/backoff, timeout, schema, sanitized previews |
| Tool/MCP | Coze plugin node and plugin config; HiAgent MCP agent/system scopes | `TOOL_CALL` supports schema mapping, write protection, permission boundary, retry/error route, sanitized evidence |
| Publish/version | Coze unpublished workflow cannot run externally, publish/history/export; HiAgent version/publish/audit | draft and published versions separated; runtime binds immutable version snapshot; definitions are reviewable |
| Node fields | Coze node form/port model; Coze Studio node type wiki | every existing field affects runtime, debug evidence, or validation; otherwise it is removed from ordinary path or marked compatibility-only |

## Screenshot-Level Reference Targets

- Coze preview/debug: node input/output, failed node marker.
- Coze running log/Trace: trace details and metrics.
- Coze code node: exception handling options and error branch.
- Coze HTTP/plugin nodes: auth, retry, output fields, tool selection.
- Coze publish/history: submit/publish history.
- HiAgent intent engine: debug/preview, custom headers/body, version selector.
- HiAgent MCP: agent-level versus system-level service scope.
- HiAgent observability: span, first-token latency, tokens.

## Uncertainty

- HiAgent public docs do not expose a full Coze-like generic workflow node taxonomy.
- `continue` is modeled as Hify's production term for Coze-like non-terminal error handling; it is inferred from official error/fallback semantics rather than copied as a literal Coze term.
- Strict HiAgent version-line parity should be rechecked if Hify later targets a specific private deployment version.
