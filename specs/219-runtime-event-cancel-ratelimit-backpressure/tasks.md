# Tasks — Spec 219

证据根目录：`artifacts/slices/219-runtime-event-cancel-ratelimit-backpressure/<slice>/`

## Slice 219.1 — SSE reconnect + cursor + DB-event-source + Redis-stream + outbox

- [ ] RED：写 `tests/contract/runtime/test_sse_reconnect.py`、`tests/integration/runtime/test_event_outbox_compensation.py`；当前应红；证据 `artifacts/219.1/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/219.1/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/219.1/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-resume-reliability.mjs`、`rtk node frontend/e2e/chatflow-resume-api.mjs` 全绿；证据 `artifacts/219.1/e2e.txt`
- [ ] Docs：新增 `docs/runtime/event-cancel-ratelimit.md`，写 "SSE reconnect / outbox compensation"
- [ ] Git commit：`feat(runtime): reliable SSE reconnect with DB event source and outbox`

## Slice 219.2 — DAG concurrent node events → frontend node state mapping

- [ ] RED：写 `rtk npm --prefix frontend run test:unit -- runtime-node-state-store` 红测；当前应红；证据 `artifacts/219.2/red.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/219.2/frontend-unit.txt`
- [ ] frontend rem：若涉视觉调整 `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/219.2/rem.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-runtime-timeline-ui.mjs`、`rtk node frontend/e2e/chatflow-running-path-animation.mjs` 全绿；证据 `artifacts/219.2/e2e.txt`
- [ ] Browser UAT：DAG fan-out 触发并发，截图节点状态对齐；证据 `artifacts/219.2/uat.md`
- [ ] Git commit：`feat(frontend): map concurrent runtime events to node state store`

## Slice 219.3 — Cancel: unstarted immediate + running cooperative + deadline

- [ ] RED：写 `tests/contract/runtime/test_cancel_unstarted_node.py`、`tests/integration/runtime/test_cooperative_cancel.py`；当前应红；证据 `artifacts/219.3/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/219.3/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/219.3/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-v2-cancel-lifecycle.mjs` 全绿；证据 `artifacts/219.3/e2e.txt`
- [ ] Browser UAT：cancel 运行中 LLM 节点，截图 deadline 生效；证据 `artifacts/219.3/uat.md`
- [ ] Git commit：`feat(runtime): cancel unstarted nodes immediately and cooperative cancel with deadline`

## Slice 219.4 — External call governance (LLM/API/Tool/Knowledge): timeout/retry/breaker/error event

- [ ] RED：写 `tests/unit/runtime/test_external_call_governance.py`，覆盖 4 个客户端类型；当前应红；证据 `artifacts/219.4/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit -q` 全绿；证据 `artifacts/219.4/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/219.4/integration.txt`
- [ ] Git commit：`feat(runtime): unify external call timeout/retry/breaker/error events`

## Slice 219.5 — Multi-level concurrency limits & queue states

- [ ] RED：写 `tests/contract/runtime/test_concurrency_limits.py`、`tests/contract/runtime/test_queue_states.py`；当前应红；证据 `artifacts/219.5/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/219.5/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/219.5/integration.txt`
- [ ] Docs：在 event-cancel-ratelimit.md 写"五级并发上限"配置
- [ ] Git commit：`feat(runtime): enforce multi-level concurrency limits and queue states`

## Slice 219.6 — High-frequency event compaction / sampling / summary

- [ ] RED：写 `tests/contract/runtime/test_event_compaction.py`，断言高频 event 被压缩 / 采样，且业务关键 event 白名单不压缩；当前应红；证据 `artifacts/219.6/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/219.6/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/219.6/integration.txt`
- [ ] Git commit：`feat(runtime): compact high-frequency events with whitelist for critical events`

## Slice 219.7 — Regression on spec 212-218 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：七 spec 入口套件重跑全绿；证据 `artifacts/219.7/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 + 217.7 + 218.8 全套；证据 `artifacts/219.7/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 219 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 219 exit regression`
