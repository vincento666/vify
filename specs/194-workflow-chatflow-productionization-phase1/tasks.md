# Tasks 194: Workflow/Chatflow Productionization Phase 1

## 194.0 Alignment and Evidence Setup

- [x] Read official Coze/HiAgent reference findings from the research subagent.
- [x] Read backend/frontend inventory findings from explorer subagents.
- [x] Create focused phase 1 spec/plan/tasks.
- [x] Save official reference mapping under the artifact directory.

## 194.1 Runtime V2 Coverage Closure

- [x] RED: prove runtime v2 rejects or falls back for `API_CALL` and `TOOL_CALL`.
- [x] Add runtime v2 `API_CALL` executor support with sanitized evidence.
- [x] Add runtime v2 `TOOL_CALL` executor support with schema mapping, retry/error policy, and sanitized evidence.
- [x] Wire LLM callable tools into runtime v2 when selected provider/model supports tools.
- [x] Update compatibility checker so supported production-safe API/Tool configs pass and unsafe configs fail with reasons.
- [x] Save slice report: modified files, RED evidence, implementation summary, gates, risks.

## 194.2 Unified Error Routing

- [x] RED: prove `continue` and `branch` are ignored for at least two named failure nodes.
- [x] Implement shared error-policy resolver for `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`, `EXECUTE_WORKFLOW`, `AGENT_CALL`.
- [x] Ensure `branch` requires connected error outlet in run/publish validation.
- [x] Ensure `continue` exposes sanitized error output and default outlet continues.
- [x] Save slice report.

## 194.3 API/Tool Production Governance

- [x] RED: prove missing auth/retry/timeout/schema/status-code policy is not enforced or evidence leaks sensitive data.
- [x] Add/complete API call governance fields in UI/API runtime mapping.
- [x] Add/complete Tool/MCP governance fields in UI/API runtime mapping.
- [x] Verify request/response previews and node debug evidence are redacted.
- [x] Save slice report.

## 194.4 Snapshot and Version Binding

- [x] RED: prove draft edits can influence a targeted published runtime v2 run or nested workflow call.
- [x] Bind runtime v2 resolver setup to immutable run definition snapshot.
- [x] Ensure nested `EXECUTE_WORKFLOW` uses published snapshot/version and records nested version refs.
- [x] Ensure version definition is readable for debug/rollback.
- [x] Save slice report.

## 194.5 Validation and Variable Contract

- [x] RED: invalid endpoint/variable/resource/model graphs can run or publish.
- [x] Harden backend publish/run validation for endpoints, variables, resources, models, and system-variable write attempts.
- [x] Keep frontend validation errors aligned with backend errors and de-duplicated in the debug dock.
- [x] Run frontend rem gate for touched UI.
- [x] Save slice report.

## 194.6 Evidence, Gates, and UAT Closure

- [x] Produce node-by-node field evidence report for all 20 node types.
- [x] Run focused unit/integration/contract gates.
- [x] Run frontend unit and `remScaleClosure`.
- [x] Run focused E2E/browser UAT with screenshots covering positive, negative, publish, run, debug.
- [x] Consolidate subagent reports and final risk list.
- [x] Mark goal complete only after requirement-by-requirement audit proves completion.
