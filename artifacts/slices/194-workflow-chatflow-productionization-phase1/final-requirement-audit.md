# Final Requirement Audit: 194 Workflow/Chatflow Productionization Phase 1

Status: complete for phase 1 scope.

## Requirement Audit

| Requirement | Evidence |
| --- | --- |
| Current 20 text node types have field save/config/runtime/debug/validation evidence | `node-field-audit-final.md`; frontend full unit `main-frontend-unit-full.txt`; backend wide gate `main-backend-workflow-wide.txt` |
| Runtime v2 is the default production path for current core workflow/chatflow nodes | `test_runtime_v2_core.py`, `test_runtime_v2_api_call_node.py`, `test_runtime_v2_tool_call_node.py`, `combined-runtime-v2-production-gate.txt` |
| Runtime binds immutable published definition snapshots | `test_runtime_v2_execute_workflow_published_snapshot.py`, `test_runtime_v2_published_version_targeting.py`, `194.4/integration.txt`, UAT version workflow `1702` |
| Node states, events, inputs, outputs, errors, elapsed/evidence are traceable | Runtime node/event APIs in backend wide gate; UAT debug run `1219`; screenshot `194.6/screenshots/runtime-v2-error-debug.png` |
| `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`, `EXECUTE_WORKFLOW`, `AGENT_CALL` support `fail / continue / branch` policy | `test_runtime_v2_core.py` standardized policy subtests; `test_runtime_v2_error_routing.py`; publish endpoint validation in `test_publish_validation.py` |
| Error branch enters endpoint validation | `194.2/red.txt`, `test_publish_validation.py`, `RuntimeV2CompatibilityChecker` tests |
| Debug model shows execution order, branch choice, variables, evidence, token/latency/failure details | Frontend debug tests: `chatflowDebugTimeline`, `chatflowRunDebug`, `workflowRunDebug`; UAT debug screenshot; `main-frontend-unit-full.txt` |
| API_CALL production governance: auth, redaction, template/schema/policy/retry/timeout/preview/evidence | `test_runtime_v2_api_call_node.py`, frontend governance tests, UAT governance panel screenshot, negative publish validation |
| TOOL/MCP governance: schema mapping, write protection, retry/error route/evidence/permission boundary | `test_runtime_v2_tool_call_node.py`, `test_publish_validation.py`, frontend governance tests, UAT governance panel screenshot |
| Variable system basics: read-only system variables, scoped variables, type/default/required/illegal ref validation | `test_publish_validation.py`, frontend variable/debug tests, `node-field-audit-final.md` |
| Draft and published versions separated; run fixed version and version definition readable | `test_workflow_publish_versions.py`, `test_runtime_v2_published_version_targeting.py`, UAT targeted v1/v2 run |
| Every existing field has runtime/debug/validation effect, not save-only | `node-field-audit-final.md`; frontend unit coverage and backend runtime/validation gates |
| Backward compatibility with old workflow/chatflow/SOP calling style | `194.6/runtime-lab-sop-compat-gate.txt` |
| Browser UAT with positive, negative, publish, run, debug screenshots/report | `194.6/uat.md`, `194.6/runtime-v2-phase1-production-uat.json`, screenshots |

## Gates

- Backend workflow unit/integration: `228 passed`, `12 subtests` in `194.6/main-backend-workflow-wide.txt`.
- Runtime v2 production focused gate: `25 passed`, `6 subtests` in `combined-runtime-v2-production-gate.txt`.
- Frontend focused/rem: `22 passed` in `main-frontend-focused-rem.txt`.
- Frontend full unit: `407 passed` in `main-frontend-unit-full.txt`.
- Runtime lab/SOP compatibility: `30 passed` in `194.6/runtime-lab-sop-compat-gate.txt`.
- Static checks: `py-compile.txt`, `ruff.txt`.
- UAT: `runtime-v2-phase1-production-uat.txt`, `uat.md`.

## Risks

- API/MCP publish-time resource health is intentionally basic: identity/contract is blocked before publish; deep live health remains runtime evidence.
- In-app Browser plugin could not attach a tab in this Codex desktop session. Real Chromium Playwright UAT passed and screenshots were visually inspected.
- Phase 2 remains explicitly excluded: Loop/Batch, SQL/database nodes, visual/file/multimedia nodes, and advanced Coze canvas operations.
