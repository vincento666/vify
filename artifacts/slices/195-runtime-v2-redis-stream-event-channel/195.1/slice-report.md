# Slice Report: 195.1 Runtime V2 Redis Stream Buffer

## 修改范围

- `app/modules/workflow/infra/realtime/redis_streams.py`
- `app/modules/workflow/infra/realtime/__init__.py`
- `app/modules/workflow/infra/chatflow_state_repository.py`
- `app/modules/workflow/web/router.py`
- `tests/integration/workflow/test_runtime_v2_redis_streams.py`
- `specs/195-runtime-v2-redis-stream-event-channel/{spec,plan,tasks}.md`
- `docs/adr/0004-realtime-control-scaleout-transport.md`

## 红测证据

- `red.txt`: 新测试因缺少 `app.modules.workflow.infra.realtime` 失败，证明 runtime v2 尚无 stream bus 抽象和 Redis stream 读取路径。

## 实现摘要

- 新增 runtime event stream bus 协议。
- 新增 `InMemoryRuntimeEventStreamBus` 用于确定性测试。
- 新增 `RedisRuntimeEventStreamBus`，由 `HIFY_REDIS_URL` 启用，写入 Redis Streams。
- `ChatflowStateRepository.append_event()` 在 DB commit 成功后发布 committed event；发布失败被吞掉，DB 事实不受影响。
- runtime v2 Chatflow/Workflow service 和后台 completion thread 注入同一个可选 bus。
- `/runtime-runs/{runId}/events/stream` 读取顺序变为 Redis stream 优先、DB `list_events` 兜底，并保持 `afterSequence` 合约。
- 旧 Chatflow SSE replay 和 runtime v2 `eventStreamRef` URL 未改变。

## 已跑门禁

- RED: `red.txt`
- Integration: `integration.txt`，3 passed
- Runtime v2 regression: `regression.txt`，9 passed
- Backend unit/integration/contract: `backend-gate.txt`，14 passed
- Static: `ruff.txt`，`py-compile.txt`
- Frontend rem: `frontend-rem.txt`，1 passed
- Frontend unit: `frontend-unit.txt`，416 passed
- Browser UAT: `browser-uat.txt`，PASS with screenshots and JSON report

## 剩余风险

- Redis Streams adapter is covered through the abstraction and in-memory deterministic bus; this slice does not require a live Redis service in CI.
- Redis stream replay currently scans the bounded per-run stream. This is acceptable for the 10k-entry realtime buffer but can be optimized with stream IDs if event volume grows.
- Customer assistant message-level events and Chatflow Session Gateway remain later phases.
