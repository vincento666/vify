# Tasks — Spec 220

证据根目录：`artifacts/slices/220-runtime-observability-ops-module/<slice>/`

## Slice 220.1 — Main menu entry, route, baseline auth gate

- [ ] RED：写 `rtk npm --prefix frontend run test:unit -- runtime-ops-router` 红测；当前应红；证据 `artifacts/220.1/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/220.1/frontend-unit.txt`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/220.1/rem.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-entry.mjs`（新增）全绿；证据 `artifacts/220.1/e2e.txt`
- [ ] Docs：新增 `docs/runtime/observability-ops-module.md` 写入口与路由
- [ ] Git commit：`feat(frontend): add runtime-ops main menu entry`

## Slice 220.2 — Run list with owner-type / state / time / tenant filters

- [ ] RED：写 `frontend/e2e/runtime-ops-list-filter.mjs`、`rtk npm --prefix frontend run test:unit -- runtime-ops-list` 红测；当前应红；证据 `artifacts/220.2/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/220.2/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-list-filter.mjs` 全绿；证据 `artifacts/220.2/e2e.txt`
- [ ] Browser UAT：四 owner type × 六 state 过滤组合，截图；证据 `artifacts/220.2/uat.md`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/220.2/rem.txt`
- [ ] Git commit：`feat(frontend): runtime-ops run list with multi-dim filters`

## Slice 220.3 — Run detail DAG view with selected/skipped/running/completed/failed/waiting

- [ ] RED：写 `rtk npm --prefix frontend run test:unit -- runtime-ops-dag-view` 红测；当前应红；证据 `artifacts/220.3/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/220.3/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-dag-view.mjs`（新增）全绿；证据 `artifacts/220.3/e2e.txt`
- [ ] Browser UAT：DAG fan-out + branch skip + waiting 截图；证据 `artifacts/220.3/uat.md`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/220.3/rem.txt`
- [ ] Git commit：`feat(frontend): runtime-ops DAG status view`

## Slice 220.4 — Node run detail: input/output summary, duration, errors, event timeline

- [ ] RED：写 `rtk npm --prefix frontend run test:unit -- runtime-ops-node-detail` 红测；当前应红；证据 `artifacts/220.4/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/220.4/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-node-detail.mjs`（新增）全绿；证据 `artifacts/220.4/e2e.txt`
- [ ] Browser UAT：包含 LLM tool call + 错误 + 事件 timeline 的节点详情截图；要点 "默认隐藏思考过程"；证据 `artifacts/220.4/uat.md`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/220.4/rem.txt`
- [ ] Git commit：`feat(frontend): runtime-ops node detail with events and errors`

## Slice 220.5 — Job queue + worker heartbeat + lease/heartbeat/attempt/next retry

- [ ] RED：写 `rtk node frontend/e2e/runtime-ops-jobs.mjs`（新增）红测；当前应红；证据 `artifacts/220.5/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit -- runtime-ops-jobs` 全绿；证据 `artifacts/220.5/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-jobs.mjs` 全绿；证据 `artifacts/220.5/e2e.txt`
- [ ] Browser UAT：job 列表 + worker 心跳 + 下次重试时间截图；证据 `artifacts/220.5/uat.md`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/220.5/rem.txt`
- [ ] Git commit：`feat(frontend): runtime-ops job queue and worker heartbeat`

## Slice 220.6 — DLQ list with retry / ignore / mark-resolved actions

- [ ] RED：写 `rtk node frontend/e2e/runtime-ops-dlq.mjs`（新增）红测；当前应红；证据 `artifacts/220.6/red.txt`
- [ ] Contract：复用 spec 218.5 `tests/contract/runtime_jobs/test_dlq_actions.py`；证据 `artifacts/220.6/contract.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit -- runtime-ops-dlq` 全绿；证据 `artifacts/220.6/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-dlq.mjs` 全绿；证据 `artifacts/220.6/e2e.txt`
- [ ] Browser UAT：DLQ 三动作截图；证据 `artifacts/220.6/uat.md`
- [ ] Git commit：`feat(frontend): runtime-ops DLQ with retry/ignore/mark-resolved`

## Slice 220.7 — Safe ops actions: cancel run / retry failed job / resume interrupted run / reopen DLQ item, with confirm

- [ ] RED：写 `rtk node frontend/e2e/runtime-ops-safe-actions.mjs`（新增）红测；当前应红；证据 `artifacts/220.7/red.txt`
- [ ] Contract：`tests/contract/runtime/test_safe_action_audit.py`（新增）断言 audit 写入；当前应红；证据 `artifacts/220.7/contract.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit -- runtime-ops-safe-actions` 全绿；证据 `artifacts/220.7/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-safe-actions.mjs` 全绿；证据 `artifacts/220.7/e2e.txt`
- [ ] Browser UAT：4 类动作 + 二次确认 + audit 写入截图；证据 `artifacts/220.7/uat.md`
- [ ] Git commit：`feat(runtime-ops): safe operator actions with confirm and audit trail`

## Slice 220.8 — Provider/API/Tool call stats + failure/retry panel

- [ ] RED：写 `rtk npm --prefix frontend run test:unit -- runtime-ops-stats` 红测；当前应红；证据 `artifacts/220.8/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/220.8/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-stats.mjs`（新增）全绿；证据 `artifacts/220.8/e2e.txt`
- [ ] Browser UAT：Provider/API/Tool 统计页 + 失败/重试面板截图；证据 `artifacts/220.8/uat.md`
- [ ] Git commit：`feat(frontend): runtime-ops provider/api/tool stats and retry panel`

## Slice 220.9 — Realtime updates via SSE + reconnect

- [ ] RED：写 `rtk node frontend/e2e/runtime-ops-realtime.mjs`（新增）红测；当前应红；证据 `artifacts/220.9/red.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-ops-realtime.mjs` 全绿；证据 `artifacts/220.9/e2e.txt`
- [ ] Browser UAT：模拟断网 + 恢复后事件续传截图；证据 `artifacts/220.9/uat.md`
- [ ] Git commit：`feat(frontend): runtime-ops realtime updates with reconnect`

## Slice 220.10 — Regression on spec 212-219 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：八 spec 入口套件重跑全绿；证据 `artifacts/220.10/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 + 217.7 + 218.8 + 219.7 全套；证据 `artifacts/220.10/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 220 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime-ops): seal spec 220 exit regression`
