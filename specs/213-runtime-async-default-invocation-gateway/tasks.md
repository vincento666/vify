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

### Slice 213.3.4 — Stop writing dispatch-irrelevant banned fields (re-carved scope)

> **范围再次 carved per builder discovery**（在 `artifacts/.../213.3.4/AUDIT.md` v2 / post-carve note 中记录）：
>
> Audit v1 漏算 3 个 production read 消费者：
> - `router.py:80` 读 `active_task.get("current_step")` 做路由决策
> - `policy.py:172` 读 `active_task["current_step"]` 判断 SOP 切换可中断性
> - `sop_adapter.py:103` 读 `request.checkpoint.current_step` 做 SOP 步骤 dispatch（`MockSopAdapter.continue_task` 按 `"collect_order_no"` / `"confirm"` 分支）
>
> 直接禁 `current_step` 写入会让这些 read 拿到 server_default 或空串 → 14 个 test 破坏（runtime_lab_service / semantic_policy / rag_policy / sop_adapter_contract）。
>
> 本 slice 缩为：
> - **In scope**: 禁写 `pending_prompt` / `collected` / `scoped_variables`（filter 到 `__chatflow` JSON key only）
> - **Out of scope** (推至 213.3.5)：
>   - 禁写 `current_step`（read consumers 需先迁移）
>   - 禁写 `business_refs`（aggregator fallback dependency）
>   - 删 `_session_business_context` delegate
>   - 删 schema 列
>   - Read migration: router.py / policy.py / sop_adapter.py 改读 adapter checkpoint in-memory 或 chatflow refs

- [ ] RED：新增 `tests/integration/runtime_lab/test_banned_writes_ignored.py` 断言 `create_checkpoint` 传入 `pending_prompt` / `collected` / `scoped_variables` 时被 ignore / filter；`update_task_state` 不写 `pending_prompt` 类字段；当前应红；证据 `artifacts/213.3.4/red.txt`
- [ ] GREEN：
  - `infra/repository.py`：
    - `create_checkpoint`：仅持久化 `status` + filter `scoped_variables` 到 `{"__chatflow": ...}`；`pending_prompt` 写 `""` 占位（NOT NULL 无 server_default）；`collected` 写 `{}`；**`current_step` 仍写 caller 传入值**（read consumers 还依赖）
    - `create_task` / `update_task_state`：**保留** `current_step` / `business_refs` 写入（read consumers 依赖）
  - `domain/service.py`：
    - 11 个 write call-sites 中：drop `pending_prompt=...` / `collected=...` 的传入；`scoped_variables=result.checkpoint.scoped_variables` **保留**（让 repository filter to `__chatflow`）
    - **保留** `current_step=` / `business_refs=` kwargs
    - 5 个 `_session_business_context` call-sites 改为直接调 `self._aggregator.collect(session_id)`
    - **保留** `_session_business_context` 1-line delegate（避免破坏 parity / delegate test）
  - `domain/chatflow_adapter.py` `_checkpoint` 仍返回完整 `SopCheckpoint` shape（dataclass 不动）
- [ ] Tests：
  - `test_chatflow_trace_api.py`：跳过 `variables.collected.route` 等业务断言，标 `@unittest.skip("213.3.5 router migration restores")`
- [ ] Backend gates：unit 374 / contract 101 / integration 463 + N (新增 banned-write tests) 不回归（特别注意 runtime_lab_service / semantic_policy / rag_policy / sop_adapter_contract 必须仍全绿，因为 `current_step` 还在写）
- [ ] Docs：AUDIT.md 后记 v2（记录 re-carve 决策）；spec.md 进度
- [ ] Git commit：`refactor(runtime-lab): stop persisting dispatch-irrelevant banned fields (pending_prompt/collected/scoped_variables)`
- [ ] 范围保护：不禁 `current_step` / `business_refs` 写入；不删 `_session_business_context`；不删 schema 列；不动 router/policy/sop_adapter read path

### Slice 213.3.5 — Drop checkpoint table + banned columns + migrate read consumers

> **范围**：完成 213.3.4 carved 出的所有工作。
>
> **拆分为 7 个 sub-slice**（详见 `artifacts/.../213.3.5/AUDIT.md`）：
>
> Audit 关键发现：
> - 总 read consumers：current_step 12 / business_refs 6 / collected 9 / pending_prompt 2 / scoped_variables 5
> - **10 个 hidden dependencies** — 历史 audit 反复漏算的根源
> - critical R2: chatflow runtime v2 必须真正 persist `conversation` scope 才能让 ban-writes 成功
> - critical R7: fake adapters 不 set `__chatflow` meta → 213.3.5a 必须修
> - 估算 11 cycles (8 baseline + 3 risk buffer)
> - R2 broken → +2 cycles

### Slice 213.3.5a — Fix fake adapters + aggregator in-memory side-channel

- [ ] RED：unit test 断言 aggregator 通过 in-memory side-channel 拿到上下文（不依赖 DB business_refs）；当前应红；证据 `artifacts/213.3.5a/red.txt`
- [ ] GREEN：
  - `aggregator.py`: 新增 `record_turn_context(session_id, context)` + `_in_memory_overlay: dict[int, dict]`；`collect()` 顺序变为 chatflow → in-memory overlay → empty
  - `service.py`: 在 `_start_task` / `_continue_active_task` / `_resume_task` / `_suspend_task` 后调 `aggregator.record_turn_context(session_id, result.collected)`
  - `_RecordingContextAdapter` / `FakeSopRuntimeAdapter._checkpoint`: set synthetic `__chatflow` meta (chatflowId / sessionId / runId / ...)
  - 验证 service 接到 fake adapter 返回 `SopCheckpoint.scoped_variables.__chatflow` 后正确写入 task ref columns
- [ ] Backend gates 不回归：unit 374 / contract 101 / integration 466
- [ ] Git commit：`feat(runtime-lab): add aggregator in-memory side-channel and synthetic __chatflow meta in fake adapters`

### Slice 213.3.5b — Migrate router/policy current_step reads to checkpoint row

- [ ] RED：unit test for router/policy 断言不再读 `task.current_step`，改读 `latest_checkpoint.current_step`
- [ ] GREEN：
  - `router.py:80` `_classify_with_keyword` 改读 latest checkpoint row（不读 task row）
  - `policy.py:172` `_classify_with_classifier` 同样
- [ ] Backend gates 不回归（特别 semantic_policy / rag_policy / handoff_policy / runtime_lab_service）
- [ ] Git commit：`refactor(runtime-lab): migrate router/policy current_step reads to latest checkpoint`

### Slice 213.3.5c — Replace _sop_checkpoint_from_row with aggregator + task refs (2 cycles)

- [ ] RED：unit test 断言 `_sop_checkpoint_from_row` 改为从 aggregator 拿 collected + 从 task ref columns 拿 __chatflow meta
- [ ] GREEN — Step 1 (refactor source)：
  - `service.py:2080`: 重写 `_sop_checkpoint_from_row` 实现：collected 从 aggregator，__chatflow 从 `task.chatflow_*` 列
  - `_chatflow_meta_from_checkpoint_row`: 改读 task row
- [ ] GREEN — Step 2 (consumer test)：
  - 验证 `_adapter_request` 拿到的 SopCheckpoint shape 与之前等价（含 collected + __chatflow meta）
  - 验证 R1：`ChatflowSopAdapter.resume_sop` 仍能拿到 collected
- [ ] Backend gates 不回归
- [ ] Git commit：`refactor(runtime-lab): rebuild SopCheckpoint from aggregator and task ref columns`

### Slice 213.3.5d — Switch _adapter_request and _suspend_task to aggregator

- [ ] RED：integration test 断言 `_adapter_request` 不再读 `task.business_refs`；`_suspend_task` 同
- [ ] GREEN：
  - `service.py:938` `_suspend_task` business_refs read 改 `self._aggregator.collect(session_id)`
  - `service.py:1315` `_adapter_request.business_refs` 改 aggregator OR 完全删除该字段（verify 无 adapter 消费它）
- [ ] Backend gates 不回归
- [ ] Git commit：`refactor(runtime-lab): _suspend_task and _adapter_request use aggregator instead of task.business_refs`

### Slice 213.3.5e-prep — Add current_step in-memory side-channel

> 起源：213.3.5e 首次 RED→GREEN 尝试中，ban `runtime_lab_checkpoint.current_step` 写入导致两个 runtime_lab_service 回归：confirm/switch arbitration 依赖 current_step progression。虽然 213.3.5b 已把 router/policy 从 task.current_step 迁到 latest_checkpoint.current_step，但 213.3.5e 进一步 ban checkpoint.current_step 后缺少替代 source。
>
> 本 prep slice 在 ban writes 前添加 current_step in-memory side-channel，类似 213.3.5a 的 business context overlay。

- [ ] RED：unit/integration test 断言 service 在 adapter result 后调用 current_step recorder，router/policy 能从 side-channel 读取 task 的 current step；当前应红；证据 `artifacts/213.3.5e-prep/red.txt`
- [ ] GREEN：新增 `RuntimeLabTurnStateCache`（或扩 aggregator）记录 `task_id -> current_step`；service 在 `_start_task` / `_continue_active_task` / `_resume_task` / `_suspend_task` 后记录；router/policy 优先读 side-channel，fallback latest_checkpoint.current_step，最后 fallback task.current_step
- [ ] Backend gates 不回归（unit / contract / integration）
- [ ] Git commit：`feat(runtime-lab): add current_step side-channel before banning checkpoint writes`
- [ ] 范围保护：不 ban writes；不删 schema；仅新增替代 source

### Slice 213.3.5e-prep2 — Durable current_step resolver from child Chatflow runtime

> 起源：213.3.5e-prep 引入了 current_step in-memory side-channel，但用户指出内存态不是最终事实源。正确目标是 durable-first：current_step / waiting node 必须优先来自 child Chatflow runtime run/checkpoint/event，而 side-channel 只能作为同进程 fast-path / fake adapter fallback。
>
> Resolver priority:
> 1. Child Chatflow runtime durable source: `runtime_v2_service.get_result(chatflow_run_id).checkpoint.pendingNodeKey`
> 2. In-memory side-channel from 213.3.5e-prep
> 3. latest `runtime_lab_checkpoint.current_step` (transition fallback)
> 4. `runtime_lab_task.current_step` (final fallback until schema drop)

- [ ] RED：unit/integration test 断言 router/policy current_step resolver 优先使用 runtime_v2 durable `pendingNodeKey`，即使 side-channel/checkpoint/task 有不同值；当前应红；证据 `artifacts/213.3.5e-prep2/red.txt`
- [ ] GREEN：新增 `RuntimeLabCurrentStepResolver`（或 service helper）读取 `task.chatflow_run_id` 后调用 `runtime_v2_service.get_result(run_id)`，从 `checkpoint.pendingNodeKey` 推导 step；无 runtime_v2_service / no runId / error 时 fallback side-channel / latest checkpoint / task
- [ ] Web wiring：`runtime_lab/web/router.py` 构造 `RuntimeLabService` 时，把 `runtime_v2_service` 注入 service（已有创建变量）；无 bindings 分支保持 None
- [ ] Tests：覆盖 priority order、BizError/error fallback、missing runId fallback
- [ ] Backend gates 不回归
- [ ] Git commit：`feat(runtime-lab): resolve current_step from child runtime before side-channel fallback`
- [ ] 范围保护：不 ban writes；不删 schema；不改 frontend/e2e

### Slice 213.3.5e-prep3 — Trace and close remaining decision-path current_step consumers

> 起源：213.3.5e retry 在 durable resolver (prep2) 后仍失败两个 runtime_lab_service 测试：`COMPLETE_TASK` 变 `CLARIFY`、`REJECT_SWITCH_CONTINUE_ACTIVE` 变 `START_SOP`。说明仍有 decision path 未使用 durable current_step resolver。
>
> 本 prep slice 先做 tracing + read-path 补齐，不 ban writes。

- [ ] RED：新增诊断/契约测试，覆盖两个失败路径，断言所有参与的 policy/router decision path 都收到 resolver 后的 current_step（runtime / side-channel / checkpoint / task priority）；当前应红；证据 `artifacts/213.3.5e-prep3/red.txt`
- [ ] GREEN：修 `RuntimeLabService._semantic_decision` / `PolicyGate` / `RuntimeLabRouter` 调用链中漏传 `latest_checkpoint` 的路径；必要时为 `pre_classifier_decision` 加 current_step-aware 参数；确保 complete/confirm/switch arbitration 使用 resolver current_step
- [ ] Targeted gates：`test_runtime_lab_service.py` 两个 previously failing tests PASS；semantic_policy / rag_policy / handoff_policy / sop_adapter_contract PASS
- [ ] Backend gates 不回归
- [ ] Git commit：`refactor(runtime-lab): route all decision paths through durable current_step resolver`
- [ ] 范围保护：不 ban writes；不改 schema；只修 read path / tests

### Slice 213.3.5e — Ban writes: current_step + collected + business_refs

- [ ] **Critical R2 verification BEFORE this slice**: 重跑 `chatflow-session-state.mjs` 确认 chatflow runtime v2 persist `conversation` scope；不通过 → STOP 升级
- [ ] **Critical current_step resolver verification BEFORE this slice**: `RuntimeLabCurrentStepResolver` priority tests + 213.3.5e-prep3 decision-path tests 全绿，且 router/policy 使用 durable runtime current_step 优先于 side-channel/checkpoint/task
- [ ] RED：扩 `test_banned_writes_ignored.py` 断言三个字段写入被 ignore；当前应红
- [ ] GREEN：
  - `repository.py` `create_task` / `update_task_state` / `create_checkpoint` 添加 ignore + warn 逻辑
  - `service.py` 所有 write call-sites drop 三个 banned kwargs
- [ ] Backend gates 不回归
- [ ] Git commit：`refactor(runtime-lab): ban writes for current_step / collected / business_refs`

### Slice 213.3.5f — Rewrite chatflow-trace router + frontend types

- [ ] RED：integration test 断言 `_runtime_task_chatflow_trace` 不读 banned cols；frontend unit test 断言新 API shape
- [ ] GREEN：
  - `web/router.py:944` `_runtime_task_chatflow_trace`: source meta from `task.chatflow_*` columns + aggregator + chatflow `state.variables.conversation`
  - 删 `_visible_scoped_variables` / `_chatflow_meta_from_checkpoint`
  - 删 `runtime_repository.get_latest_checkpoint(...)` 调用
  - frontend `runtimeLab.ts:213,264` 类型调整 (`currentStep` optional, `businessRefs` source from aggregator)
  - frontend test fixtures 4 处更新
- [ ] frontend rem：若涉视觉尺寸 → remScaleClosure
- [ ] E2E：`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` 全绿
- [ ] Browser UAT：chatflow-trace 面板 + 客服侧 SOP 切换 / 暂停 / 恢复场景；证据 `artifacts/213.3.5f/uat.md` + `screenshots/`
- [ ] Git commit：`refactor(runtime-lab): chatflow-trace router uses task ref columns and aggregator`

### Slice 213.3.5g — Schema drop + delete delegate + final cleanup

- [ ] RED：schema-level test 断言 `runtime_lab_task` 不含 `current_step` / `business_refs`；`runtime_lab_checkpoint` 表不存在
- [ ] GREEN — Step C:
  - `infra/schema.py` 移除 `runtime_lab_checkpoint` 表 + `runtime_lab_task.current_step` / `business_refs` 列
  - `infra/repository.py` 删 `create_checkpoint` / `get_checkpoint` / `get_latest_checkpoint`
  - `domain/service.py` 删 `_sop_checkpoint_from_row` (已 deprecated 后) / `_session_business_context` delegate
  - `domain/payload.py` 删 `currentStep` / `businessRefs` / `collected` / `scoped` keys
  - Migration: ALTER TABLE DROP COLUMN + DROP TABLE (mysql ok; sqlite recreate)
- [ ] Tests cleanup:
  - `test_mysql8_runtime_v2_customer_assistant_persistence.py:1019-1020` 更新 column list
  - `test_business_context_aggregator_parity.py:121` 改调 `aggregator.collect()` 而非 `_session_business_context`
  - `test_service_uses_aggregator.py:36-44` 同
- [ ] Backend gates 不回归
- [ ] E2E：`rtk node frontend/e2e/chatflow-session-state.mjs`、`chatflow-resume-api.mjs` 全绿
- [ ] Browser UAT：客服侧 SOP 切换完整场景
- [ ] Docs：`docs/chatflow-sop-state-boundary.md` 终稿（ledger 字段最终集）；AUDIT.md 状态 ✅
- [ ] Git commit：`refactor(runtime-lab): drop checkpoint table and banned columns; finalize SOP state boundary`

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
