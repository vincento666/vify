# Slice 验收门禁

每个 slice 都必须按以下顺序执行。没有前一个门禁的证据，不进入下一个门禁。

## 1. RED Gate

目的：证明测试确实覆盖了尚未实现或尚未迁移的行为。

要求：

- 新增一个行为测试，优先从 public API 或用户路径进入。
- 运行测试并确认失败原因正确，不是语法错误、导入错误或测试环境错误。
- 保存输出到 `artifacts/slices/{spec}/{slice}/red.txt`。

示例命令：

```bash
pytest tests/contract/test_provider_api.py -k create_provider
```

## 2. Unit Gate

目的：证明 slice 内的纯逻辑正确。

要求：

- Pydantic schema、错误码映射、parser、workflow condition、SSE event encoder
  等纯逻辑必须有单测。
- 不允许只靠 E2E 覆盖复杂逻辑。

示例命令：

```bash
pytest tests/unit
```

## 3. Integration / Contract Gate

目的：证明 FastAPI route、SQLAlchemy、Alembic schema 和 Redis/外部边界契约正确。

要求：

- API 返回 envelope `{code,message,data}`。
- 错误码与当前 Java 版语义兼容。
- 数据库行为通过 SQLAlchemy/Alembic，不直接依赖实现细节。

示例命令：

```bash
pytest tests/integration tests/contract
```

## 4. E2E Gate

目的：证明前后端组合路径可工作。

要求：

- 使用 Playwright 或等价真实浏览器驱动。
- 覆盖 slice 的主要用户路径。
- 保存输出到 `artifacts/slices/{spec}/{slice}/e2e.txt`。

示例命令：

```bash
npm --prefix hify-web run build
pytest tests/e2e
```

## 5. Browser UAT Gate

目的：从用户视角确认页面结果和交互符合预期。

要求：

- 打开真实浏览器页面。
- 记录操作步骤、期望结果、实际结果。
- 保存截图到 `artifacts/slices/{spec}/{slice}/screenshots/`。
- 涉及 spec 核心价值的真实用户路径时，必须沉淀可重复脚本或可复放的内置浏览器
  自动化步骤；纯人工观察不能作为最终完成证据。

UAT 记录模板：

```md
# UAT

- Spec:
- Slice:
- URL:
- Browser:
- Steps:
- Expected:
- Actual:
- Screenshots:
- Verdict: PASS / FAIL
```

## 6. Real-case Automated UAT Gate

目的：用真实案例和真实边界证明 spec 的产品价值，而不是只证明 mock 或单元逻辑。

适用场景：

- 外部 LLM / embedding / reranker / tool-calling provider。
- 真实业务 API、真实 adapter、真实 sandbox、staging 或 contract-backed live service。
- 真实数据流、真实权限/审批、真实审计或成本预算。
- 用户要求“真实案例 UAT”或 spec 的验收价值依赖真实外部系统。
- 当前 spec 明确要求 live LLM，即使业务 adapter 是 mock/seam，也必须用真实外部
  provider 走通模型路径。

要求：

- spec 立项时必须写清真实案例、真实服务边界、凭据注入方式、预算、数据集、断言和
  artifact 路径。
- 用自动化脚本或内置浏览器控制走通真实案例；人工 UAT 只可辅助发现问题。
- 外部副作用必须使用 sandbox、dry-run、quote、可逆操作或 compensation path，并保存
  审批、幂等键、补偿和审计证据。
- artifact 必须保存 redacted request/response metadata、截图、日志、trace/audit export、
  token/cost/context budget 和最终结果。
- 缺少 key、quota、网络、sandbox、测试数据或预算时，结果为 `BLOCKED` /
  `waiting-human`，不能标记 PASS，不能静默 skip。
- Domain adapter 是否连接真实业务系统服从当前 spec 边界；不要把“真实案例”自动
  扩写成“必须接真实业务系统”。

最小记录模板：

```md
# Real-case UAT

- Spec:
- Slice:
- External service:
- Credential env/key ref:
- Scenario:
- Test data:
- Side-effect boundary:
- Command / browser automation:
- Objective assertions:
- Audit export:
- Screenshots:
- Verdict: PASS / FAIL / BLOCKED
```

## 7. Docs Gate

目的：让规格文档和真实实现同步。

要求：

- 更新对应 `spec.md` slice 状态。
- 更新 `tasks.md` 完成项。
- 如发生架构决策变化，新增或更新 ADR。

## Chrome-MCP UAT Harness

部分 e2e 脚本使用 Chrome-MCP 注入的 `browser.tabs.selected()` /
`tab.playwright` 入口而非 plain Playwright 启动方式。这类脚本要求测试侧
已有一个登录态浏览器 Tab，通常通过 MCP / 协作执行环境提供，不可用
`node frontend/e2e/<file>.mjs` 直接跑。

### 识别 Chrome-MCP 依赖脚本

grep 入口判定：

```bash
rtk grep -l "browser\.tabs\.selected\|tab\.playwright" frontend/e2e/*.mjs
```

当前已知 Chrome-MCP harness 脚本：

- `frontend/e2e/chatflow-inapp-deep-tree-uat.mjs`
- `frontend/e2e/chatflow-inapp-visible-output-uat.mjs`
- `frontend/e2e/workflow-chatflow-node-form-controls-inapp-uat.mjs`
- `frontend/e2e/workflow-inapp-visible-output-uat.mjs`

新增脚本如果使用 `browser.tabs.selected()` 或 `tab.playwright`，必须在
本节列表中登记。

### 调用约定

| 场景 | 入口约定 |
|------|---------|
| 本机 Chrome-MCP 已就绪 | Claude Code / Codex Desktop 通过 MCP 工具 `browser` 命名空间直接驱动 |
| Headless / CI | 暂不支持；脚本应能优雅拒绝并返回 ENV-BLOCKED-CHROME-MCP |
| 切换 base URL | 通过 `HIFY_E2E_BASE_URL` 环境变量传入；默认 `http://127.0.0.1:5173` |

### Screenshot 与日志归档

Chrome-MCP 脚本生成的 screenshot 必须写入：

```
artifacts/slices/<spec-id>/<slice-id>/screenshots/<scenario>/<step>.png
```

执行日志：

```
artifacts/slices/<spec-id>/<slice-id>/uat-runs/<script-name>.log
```

不要写入 `frontend/e2e/screenshots/` 仓内目录，避免被脚本反复覆盖污染历史证据。

### 判定关键字

UAT 报告 / addendum 必须使用以下大写关键字之一，便于 grep / orchestrator 解析：

| 关键字 | 含义 |
|--------|------|
| `PASS` | 脚本完整执行且断言全绿 |
| `LOGIC-RED` | 脚本执行至某行失败，根因在业务代码（不修脚本） |
| `INFRA-RED` | 脚本执行时报路径/工具/导入错误（非业务） |
| `ENV-BLOCKED-CHROME-MCP` | 缺 Chrome-MCP harness，无法启动 |
| `ENV-BLOCKED-PGVECTOR` | 缺 pgvector / postgres，无法继续 |
| `ENV-BLOCKED-LIVE-MODEL` | 缺真实 LLM key / quota / provider access，live gate 阻塞，不可记 PASS |

### 不允许的实践

- 不允许把 `tab.playwright` 调用改写为 `await chromium.launch()` 来"让脚本能在 plain node 跑"；
  这等于把 Chrome-MCP 契约改成 plain Playwright，绕过了登录态 Tab 复用语义。
- 不允许通过 `--ignore` / `-k` 在 CLI 上排除这些脚本来让 baseline gate 假装全绿。
- 不允许在 acceptance-gates 之外的位置定义脚本入口约定。
- 不允许把 Chrome-MCP 脚本拷贝出第二份用 plain Playwright 重写；如确有此需要，必须新建 spec slice 立项。

### Slice 引用方式

任何 slice 在其 `tasks.md` 列 Browser UAT 项时，若涉及 Chrome-MCP 脚本，
必须显式注明 `Chrome-MCP harness（见 docs/testing/acceptance-gates.md
§ Chrome-MCP UAT Harness）`，并把脚本入口和 ENV-BLOCKED 判定关键字
写入 `uat.md`。

## Opt-in Live Gates

默认 CI 可以不跑真实外部模型，但当 active spec 把外部 LLM 或真实业务系统列为
必过项时，最终 slice / release gate 必须显式 env 打开并保存 artifact。缺少 live
前置条件只能记录 `ENV-BLOCKED-LIVE-MODEL` 或对应 BLOCKED artifact，不能作为完成证据。

### Customer Assistant Live ReAct Acceptance

- Gate: `customer-assistant-live-react-acceptance`
- Test:
  `PYTHONPATH=. uv run pytest tests/acceptance/test_customer_assistant_live_react_acceptance.py -q`
- Enable:
  `HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE=1`
- API key:
  `HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY` or `OPENROUTER_API_KEY`
- Base URL default: `https://openrouter.ai/api/v1`
- Model pool default:
  `xiaomi/mimo-v2-flash,qwen/qwen3.5-9b,deepseek/deepseek-v4-flash`
- Artifact:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/live/customer-assistant-live-react-acceptance.md`
- Default CI evidence:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/acceptance-skip.txt`

## Default-async runtime contract (spec 213.2)

Chatflow / Workflow debug run endpoints must:

- Return the six-ref envelope (`runId`, `statusRef`, `eventsRef`,
  `eventStreamRef`, `nodesRef`, `resultRef`) within the initial response,
  not block on completion.
- Tag the envelope with `runtimeMode = "async-durable"` (default) or
  `"sync"` (explicit fallback via `start_and_wait` or `/runs-legacy`).
- Be uniformly accessible via `RuntimeInvocationRefs.from_envelope(...)`.

Any new slice touching Chatflow / Workflow run paths must re-verify this
contract via `tests/integration/runtime/test_debug_runs_default_async.py`.

Both `/runs` and `/runs-v2` aliases serve the same async-durable
handler at present; integration tests pin both paths. Physical
de-duplication tracked in slice 213.X-unify-runs-v2.

## Slice Done 定义

一个 slice 只有在以下条件都满足时才算完成：

- RED 证据存在。
- Unit 通过。
- Integration/Contract 通过。
- E2E 通过或有明确“不涉及 UI”的记录。
- Browser UAT 通过或有明确“不涉及 UI”的记录。
- 文档状态已更新。
