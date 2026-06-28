# Tasks — Spec 213

证据根目录：`artifacts/slices/213-runtime-async-default-invocation-gateway/<slice>/`

## Slice 213.1 — RuntimeInvocationGateway Protocol & six-ref DTO

- [ ] RED：在 `tests/contract/runtime_gateway/test_six_ref_dto.py`（新增）断言 gateway 返回 runId/statusRef/eventsRef/eventStreamRef/nodesRef/resultRef 六字段；`rtk uv run pytest tests/contract/runtime_gateway -q` 当前应红；证据 `artifacts/213.1/red.txt`
- [ ] GREEN：在 `app/modules/runtime/api/facade.py` 增加 `RuntimeInvocationGateway` Protocol 与 `RuntimeInvocationRefs` DTO
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/213.1/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_gateway -q` 全绿；证据 `artifacts/213.1/contract.txt`
- [ ] Docs：spec.md 引用六元组字段；在 `specs/211-*/stream-refs-matrix.md` 标注 213.1 已扩字段
- [ ] Git commit：`feat(runtime): define invocation gateway six-ref DTO`

## Slice 213.2 — Chatflow & Workflow debug runs default to async durable

- [ ] RED：写 `tests/integration/runtime/test_chatflow_debug_default_async.py`、`test_workflow_debug_default_async.py`，断言默认请求返回 refs 而非完成结果；当前应红；证据 `artifacts/213.2/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q`、`tests/unit/workflow -q`、`tests/unit/chatflow -q` 全绿；证据 `artifacts/213.2/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/213.2/integration.txt`
- [ ] Frontend Unit：相关 store / runner 迁移测试 `rtk npm --prefix frontend run test:unit -- chatflow-runner workflow-runner`；证据 `artifacts/213.2/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-run-debug-deeplink.mjs`、`rtk node frontend/e2e/workflow-chatflow-llm-run.mjs`、`rtk node frontend/e2e/chatflow-run-optimistic-loading.mjs` 全绿；证据 `artifacts/213.2/e2e.txt`
- [ ] Browser UAT：核心 Chatflow / Workflow 调试页面截图 async refs 显示；证据 `artifacts/213.2/uat.md` + `screenshots/`
- [ ] frontend rem：若 runner 卡片样式调整 `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
- [ ] Docs：在 `docs/testing/acceptance-gates.md` 增加 "default-async runtime contract" 一行
- [ ] Git commit：`feat(chatflow,workflow): default debug runs to durable async runtime`

## Slice 213.2.1 — Migrate chatflow-run-optimistic-loading e2e to async runtime mock surface

> 起源：slice 213.2 把"默认 async durable"用 contract 锁定后，e2e `chatflow-run-optimistic-loading.mjs` 整脚本验证暴露 mock 锁在 sync 时代。原计划仅刷新 mock URL，执行中发现 mock URL + mock response body + 缺失的 polling endpoint stub 是**一起**的问题：
>
> - mock URL pinned at `/api/v1/chatflows/*/runs-legacy`，但 production frontend `runChatflowV2` 实际用 `/api/v1/chatflows/*/runs-v2`
> - mock fulfill body 仍是 sync envelope（`status: 'SUCCEEDED', inline output, streamEvents`），但 production V2 runner 收到响应后会去 poll `/runtime-runs/{id}`（status / events / result），mock 假 runId 在真 backend 找不到，触发 `Runtime v2 run not found`
> - 必须**整体迁移到 async runtime mock surface**：mock URL 改 `/runs-v2`，response body 改 six-ref envelope，加 polling endpoint stub
>
> 范围：仅 e2e mock 层迁移，**不动 production code**，**不动 e2e 业务断言**（`runRequestSeen`、optimistic-loading bubble 可见、最终输出替换 bubble 三条断言保留语义）。

- [ ] RED：重跑 `chatflow-run-optimistic-loading.mjs`，固化"mock URL 不命中 + V2 runner 找不到 mock runId"的双重失败；证据 `artifacts/213.2.1/red.txt`
- [ ] 静态定位：grep 脚本中所有 `page.route(...)` 配置，列出当前 mock surface
- [ ] Fix 第 1 部分 - mock URL：`page.route("**/api/v1/chatflows/*/runs-legacy", ...)` → `page.route("**/api/v1/chatflows/*/runs-v2", ...)`
- [ ] Fix 第 2 部分 - mock fulfill body：从 sync envelope 改为 six-ref envelope，包含：
  - `runId: <number>`
  - `status: "RUNNING"`
  - `statusRef: "/api/v1/runtime-runs/{runId}"`
  - `eventsRef: "/api/v1/runtime-runs/{runId}/events"`
  - `eventStreamRef: "/api/v1/runtime-runs/{runId}/events/stream?afterSequence=0"`
  - `nodesRef: "/api/v1/runtime-runs/{runId}/nodes"`
  - `resultRef: "/api/v1/runtime-runs/{runId}/result"`
  - `runtimeMode: "async-durable"`
  - `runtimeRefs: {runId, statusRef, eventsRef, eventStreamRef, nodesRef, resultRef}`
- [ ] Fix 第 3 部分 - polling endpoint stub：加 `page.route` 拦截：
  - `GET **/api/v1/runtime-runs/{runId}` → 返回 status / result（让脚本能进入 SUCCEEDED 状态）
  - `GET **/api/v1/runtime-runs/{runId}/events` → 返回 events list
  - `GET **/api/v1/runtime-runs/{runId}/result` → 返回 output
  - 可选 `GET **/api/v1/runtime-runs/{runId}/events/stream` SSE mock（若 production runner 用 SSE 拿事件）
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-run-optimistic-loading.mjs` PASS；证据 `artifacts/213.2.1/e2e.txt`
- [ ] Browser UAT：留 optimistic-loading bubble 在 in-flight async request 期间可见的截图 + 最终输出替换 bubble 的截图；证据 `artifacts/213.2.1/uat.md` + `screenshots/`
- [ ] frontend rem：不涉视觉尺寸（e2e mock 改动）→ 跳过，记录 N/A
- [ ] Backend gates 不回归：`rtk uv run pytest tests/integration -q` 全绿（450 passed）；证据 `artifacts/213.2.1/integration.txt`
- [ ] Docs：baseline.md 追加 "chatflow-run-optimistic-loading e2e migrated to async mock surface → GREEN @ slice 213.2.1"
- [ ] Git commit：`fix(e2e): migrate chatflow-run-optimistic-loading to async runtime mock surface`
- [ ] 范围保护：仅改 mock 层 (URL + response body + polling stub)；**不动业务断言、不动 production code、不动其它 e2e**。若发现 production code 也需改才能 PASS → STOP 升级

## Slice 213.2.2 — Extend default-async contract to /runs-v2

> 起源：slice 213.2 的 integration test 只断言了 `POST /api/v1/{workflows,chatflows}/{id}/runs` 路径，但 backend 同时有 `/runs-v2` 路径（`run_workflow_v2` / `run_chatflow_v2` handler）。**两个 handler 代码完全相同** — 都调 `_start_workflow_runtime_v2_gateway` / `_start_chatflow_runtime_v2_gateway`，envelope shape 相同。frontend `runChatflowV2` 用的是 `/runs-v2`，所以 213.2 锁了一个无人 enforce 的入口。
>
> 本 slice 不动 production handler 代码（两条路径本就一致），仅扩 integration test 同时断言 `/runs` 和 `/runs-v2` 都 emit `runtimeMode=async-durable` + 六字段 refs，让 contract 真正覆盖 frontend 调用路径。物理统一两个 alias 延后到 213.X-unify-runs-v2。

- [ ] RED：在 `tests/integration/runtime/test_debug_runs_default_async.py` 加 2 个新 case 断言 `/runs-v2` 同样 emit `runtimeMode=async-durable` + 六字段；当前应红（test 不存在 = "未覆盖" 视为 RED）；证据 `artifacts/213.2.2/red.txt`
- [ ] GREEN：因为 `/runs-v2` handler 已经调用同一个 gateway，新测试应该直接 PASS；证据 `artifacts/213.2.2/green.txt`
- [ ] Backend gates 不回归：unit 368 / contract 101 / integration 445 + 3 (213.2) + 2 (本 slice) = 450
- [ ] Docs：在 `docs/testing/acceptance-gates.md` § Default-async runtime contract 章节追加一段："Both `/runs` and `/runs-v2` aliases serve the same async-durable handler at present; integration tests pin both paths. Physical de-duplication tracked in slice 213.X-unify-runs-v2."
- [ ] Git commit：`test(runtime): extend default-async contract to /runs-v2 alias`

## Slice 213.X-unify-runs-v2 — Retire /runs-v2 alias

> **立项时机**：spec 213 收尾（213.6 regression 之后）或独立 spec。**不阻塞** spec 213.3 / 213.4 / 213.5 / 213.6 / 213.7 推进。
>
> `/runs` 和 `/runs-v2` 两个 handler 代码完全相同，frontend 调 `/runs-v2`、backend `/runs` 同时存在等于 URL alias。物理统一：删 `run_workflow_v2` / `run_chatflow_v2` handler、frontend `runChatflowV2` 改调 `/runs`、扫描所有 e2e mock 把 `/runs-v2` 改 `/runs`。

- [ ] RED：grep 全仓 `/runs-v2`、`runs-v2`、`runChatflowV2`、`workflow_run_v2` 等关键字，列影响清单（预计 backend 2 handler、frontend 1 API client、N 个 e2e mock）；证据 `artifacts/213.X/red.txt`
- [ ] 删 backend `run_workflow_v2` 和 `run_chatflow_v2` 两个路由（保留 `_start_*_runtime_v2_gateway` 内部函数）
- [ ] 改 frontend `frontend/src/api/workflow.ts`（或同等位置）`runChatflowV2` URL `/runs-v2` → `/runs`
- [ ] 扫描所有 e2e mock：`rtk grep -rln "runs-v2" frontend/e2e/` 改成 `/runs`
- [ ] Unit / Integration / Contract 全套不回归
- [ ] Frontend unit / rem 不回归
- [ ] E2E：全部跟 chatflow/workflow 运行相关的脚本 PASS，特别是之前用 `/runs-v2` mock 的
- [ ] Browser UAT：手验 chatflow / workflow debug run 仍可正常发起
- [ ] Docs：acceptance-gates.md § Default-async runtime contract 章节去掉"two aliases"备注，spec 213.2.2 标完成
- [ ] Git commit：`refactor(runtime): retire /runs-v2 alias in favour of unified /runs`
- [ ] 范围保护：仅 URL alias 物理统一；不动 V2 invocation gateway 任何业务逻辑

## Slice 213.3 — SOP Router returns runtime refs and stops mirroring Chatflow state

> **拆分为 6 个 sub-slice**。完整 audit 见 `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/AUDIT.md`。
>
> Audit 关键发现：
> - schema 6 个禁字段（`runtime_lab_task.current_step`、`runtime_lab_task.business_refs`、`runtime_lab_checkpoint.{current_step, pending_prompt, collected, scoped_variables}`）
> - service.py 71 个引用（~32 写 ~39 读）
> - 4/9 API endpoint 暴露禁字段
> - 20 test 文件受影响
> - `_session_business_context` 是聚合 linchpin，需替换为 child-Chatflow aggregator
> - `ChatflowAdapter._checkpoint.scoped_variables.__chatflow` 已携带真实 chatflow refs — 把它提升为 first-class columns
> - 213.7 (chatflow_sop race) 是 customer-assistant 模块的同款 mirror anti-pattern，独立修

### Slice 213.3.1 — Introduce runtime ref columns + dual-write

- [ ] RED：扩 `tests/integration/runtime_lab/test_runtime_lab_repository.py`，断言 `create_task` 接受并持久化新列 (`chatflow_id`, `chatflow_session_id`, `chatflow_run_id`, `chatflow_event_id`, `chatflow_checkpoint_id`, `runtime_version`)；当前应红；证据 `artifacts/213.3.1/red.txt`
- [ ] GREEN：在 `infra/schema.py` 给 `runtime_lab_task` 加 6 个 nullable 列；`infra/repository.py` 的 `create_task`/`update_task_state` 接受 + 持久化；`domain/service.py` 的 `_start_task` 从 `result.checkpoint.scoped_variables.__chatflow` 读取后 dual-write；旧禁字段仍写（向后兼容）
- [ ] Unit：`rtk uv run pytest tests/unit/runtime_lab -q` 全绿
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_lab -q` 全绿
- [ ] Backend gates：unit / contract / integration 不回归
- [ ] Docs：spec 213.3 AUDIT.md 状态更新 "213.3.1 ✅"
- [ ] Git commit：`feat(runtime-lab): add runtime ref columns to task and dual-write from chatflow adapter`

### Slice 213.3.2 — Expose runtime refs on /messages envelope + format_task

- [ ] RED：扩 `tests/contract/test_chatflow_run_gateway_api.py` 或新增 `tests/integration/runtime_lab/test_messages_runtime_refs.py`，断言 `/messages` 和 `/sessions/{id}/messages` 响应含 `chatflowSession` 块（`chatflowId / runId / eventId / checkpointId / sessionId / statusRef / eventsRef / eventStreamRef / nodesRef / resultRef / runtimeVersion`）；当前应红；证据 `artifacts/213.3.2/red.txt`
- [ ] GREEN：`domain/payload.py` 加 `chatflowSession` projection helper；`domain/service.py` 的 `_task_summary` 和 `format_turn` 调用；`web/router.py` 复用 `/sessions/{id}/chatflow-trace` 的现有 helper
- [ ] Frontend Unit：runtime-lab message 接口消费者新增 chatflowSession 字段消费契约（如不存在 → 待 213.3.3 之后补）
- [ ] E2E：`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` 全绿（envelope 含新字段 + 老字段）
- [ ] Backend gates：不回归
- [ ] Docs：AUDIT.md 状态 + spec 213.2 contract section 引用 213.3.2
- [ ] Git commit：`feat(runtime-lab): expose chatflowSession refs on /messages envelope`

### Slice 213.3.3 — Replace _session_business_context with child-Chatflow aggregator

- [ ] RED：新增 `tests/integration/runtime_lab/test_session_business_context_aggregator.py`，断言 `_session_business_context` 从 child Chatflow runtime 拉 `conversation_variables` 而非读 `business_refs` / `collected`；mock chatflow runtime 返回 fresh variables，断言 aggregator 优先 child runtime 数据；当前应红；证据 `artifacts/213.3.3/red.txt`
- [ ] GREEN：新增 `domain/aggregator.py`（或扩 `ChatflowAdapter`）`RuntimeLabAggregator` — 给定 session 走 active+suspended tasks，per (sessionId/runId) 调用 chatflow runtime 拿 `conversation_variables`；service.py ~10 个 call-sites 切换到 aggregator
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_lab -q` 全绿 — **特别 golden tests on context-reference flows**（防 silently 丢失 user-provided slots）
- [ ] Backend gates：unit / contract / integration 不回归
- [ ] Docs：AUDIT.md + 新增 `docs/chatflow-sop-state-boundary.md` 草稿，说明 aggregator 边界
- [ ] Git commit：`refactor(runtime-lab): replace business_context mirror with child-Chatflow aggregator`
- [ ] 范围保护：仅替换读路径；写路径暂不动（213.3.4 处理）

### Slice 213.3.4 — Stop writing banned fields

- [ ] RED：扩 repository test 断言 `create_task`/`update_task_state`/`create_checkpoint` 调用时即使传入 `current_step`/`pending_prompt`/`collected`/`scoped_variables` 也不写库（被 ignore 或仅持久化 `__chatflow` 部分）；当前应红；证据 `artifacts/213.3.4/red.txt`
- [ ] GREEN：`infra/repository.py` `update_task_state`/`create_task` ignore 禁字段（log warning）；`create_checkpoint` 仅持久化 `status` + `__chatflow`；`domain/service.py` 所有写路径 drop 禁字段；`domain/chatflow_adapter.py` `_checkpoint` 仍返回这些字段（暂保留 in-memory），但 service 写入时 drop
- [ ] Unit / Integration：全绿；`SopCheckpoint` dataclass 暂时保留 shape（不动外部契约）
- [ ] Backend gates：不回归
- [ ] Docs：AUDIT.md
- [ ] Git commit：`refactor(runtime-lab): stop persisting banned fields on task and checkpoint writes`

### Slice 213.3.5 — Drop runtime_lab_checkpoint table + banned columns

- [ ] RED：新增 schema-level test 断言 `runtime_lab_task` 不含 `current_step` / `business_refs` 列，且 `runtime_lab_checkpoint` 表不存在；当前应红；证据 `artifacts/213.3.5/red.txt`
- [ ] GREEN：`infra/schema.py` 移除 `runtime_lab_checkpoint` 表 + `runtime_lab_task.current_step`/`business_refs` 列；`infra/repository.py` 删 `create_checkpoint`/`get_checkpoint`/`get_latest_checkpoint`；`domain/service.py` 删 `_sop_checkpoint_from_row`/`_chatflow_meta_from_checkpoint_row`/`_visible_scoped_variables`；`domain/payload.py` 删 `currentStep`/`businessRefs`/`collected`/`scoped` keys；`web/router.py` `_runtime_task_chatflow_trace` 改读 task ref columns + aggregator
- [ ] Frontend Unit：`chatflow-trace` panel 测试更新（如有），改读 `chatflowSession.*` 而非 `currentStep`/`collected`
- [ ] Frontend rem：若涉视觉尺寸 → 跑 remScaleClosure
- [ ] E2E：`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs`、`chatflow-session-state.mjs`、`chatflow-resume-api.mjs` 全绿
- [ ] Browser UAT：客服侧 SOP 切换 / 暂停 / 恢复场景；chatflow-trace 面板仍正常显示；证据 `artifacts/213.3.5/uat.md`
- [ ] Backend gates：不回归
- [ ] Docs：AUDIT.md + `docs/chatflow-sop-state-boundary.md` 终稿（ledger 字段最终集）
- [ ] Git commit：`refactor(runtime-lab): drop checkpoint table and banned columns; chatflow-trace uses runtime refs`

### Slice 213.3.6 — Deprecate FakeSopRuntimeAdapter for production paths

- [ ] RED：unit test 断言 service 在 production bootstrap 不接受 `FakeSopRuntimeAdapter`；当前应红；证据 `artifacts/213.3.6/red.txt`
- [ ] GREEN：`domain/service.py` / `domain/sop.py` 加 binding 验证：sop_id 无 chatflow binding 时返回 `MISSING_CHATFLOW_BINDING` 错误；`FakeSopRuntimeAdapter` 仅在 test bootstrap 接受
- [ ] Unit / Integration：不回归（已注册的 SOP 仍答得了；未注册的报 hard error）
- [ ] UAT：confirm registered SOP IDs still answer
- [ ] Docs：AUDIT.md
- [ ] Git commit：`refactor(runtime-lab): require explicit chatflow binding; deprecate FakeSopRuntimeAdapter for production`

### Slice 213.3 (parent) — Sealing slice

- [ ] 所有 6 个 sub-slice 已 GREEN
- [ ] `tests/integration/runtime_lab/test_sop_router_async_refs.py` + `tests/unit/runtime_lab/test_sop_router_ledger_schema.py` 最终断言 ledger 仅保存 conversation/active-child/suspended/route history/resume offer/intent summary 字段 — 全绿
- [ ] `docs/chatflow-sop-state-boundary.md` 终稿
- [ ] Spec 213 baseline.md 追记 "spec 213.3 closed @ SHA <sha>"
- [ ] Git commit：`docs(specs): seal slice 213.3 SOP Router state mirror removal`

## Slice 213.4 — Customer-assistant worker returns async refs by default

- [ ] RED：写 `tests/integration/customer_assistant/test_worker_default_async_refs.py`，断言默认 worker 调用 Chatflow / SOP 返回 runId + refs；当前应红；证据 `artifacts/213.4/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/customer_assistant -q` 全绿；证据 `artifacts/213.4/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/customer_assistant -q` 全绿；证据 `artifacts/213.4/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs`、`rtk node frontend/e2e/chatflow-transfer-to-human-node.mjs` 全绿；证据 `artifacts/213.4/e2e.txt`
- [ ] Docs：在 `docs/customer-assistant-runtime.md`（如缺则新增）记录默认 async refs 行为与 `--sync` 显式 fallback
- [ ] Git commit：`feat(customer-assistant): worker defaults to async runtime refs`

## Slice 213.5 — Disconnect recovery via runId returns status/events/nodes/result

- [ ] RED：写 `tests/contract/runtime_recovery/test_runid_recovery.py`，断言通过 runId 可在断线后重建 status / events (afterSequence=N) / nodes / result；当前应红；证据 `artifacts/213.5/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 不回归；证据 `artifacts/213.5/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_recovery -q` 全绿；证据 `artifacts/213.5/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-resume-reliability.mjs`、`rtk node frontend/e2e/chatflow-resume-api.mjs` 全绿；证据 `artifacts/213.5/e2e.txt`
- [ ] Docs：在 `specs/211-*/stream-refs-matrix.md` 增加 "recovery" 列
- [ ] Git commit：`test(runtime): cover runId-based disconnect recovery`

## Slice 213.6 — Regression on spec 212 entry gates

- [ ] Unit：`rtk uv run pytest tests/unit -q` 全绿；证据 `artifacts/213.6/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/213.6/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract -q` 全绿；证据 `artifacts/213.6/contract.txt`
- [ ] Frontend unit / rem：`rtk npm --prefix frontend run test:unit` 和 `... src/remScaleClosure.test.ts` 全绿；证据 `artifacts/213.6/frontend-unit.txt`、`rem.txt`
- [ ] Browser UAT：spec 212.5 整套脚本全绿；证据 `artifacts/213.6/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 213 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 213 exit regression`
