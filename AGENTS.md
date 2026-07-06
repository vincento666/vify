# Hify Python 迁移协作规范

当前目标：把 `socutes/hify` 现有功能边界复刻到
`Python 3.12 + FastAPI + SQLAlchemy 2.0`。迁移按 Spec Kit + TDD 逐 slice 推进，
不是逐文件翻译 Java。

## 不可变原则

1. 先复刻，后增强：`001` 到 `008` 只复刻已有功能边界和 Mock 行为；真实 RAG、
   tool calling、MCP 强化放到 `009` 和 `010`。
2. API 兼容优先：前端仍使用 `/api/v1/...`，响应 envelope 保持
   `{code, message, data}`。
3. Python 固定 3.12，`requires-python` 使用 `>=3.12,<3.13`。
4. Spec 先行：每个 feature 先有 `spec.md`、`plan.md`、`tasks.md`，再实现。
5. TDD 强制：每个 slice 先写红测并保存失败证据，再写最小实现。
6. 门禁串行：一个 slice 未通过全部门禁，不得进入下一个 slice。
7. 影响前端或用户流程的 slice 必须执行真实浏览器 UAT 并保存证据。
8. Spec 立项必须定义真实案例自动化 UAT：涉及真实外部模型、真实业务系统、
   真实数据流或真实用户价值的能力，必须用可重复脚本走通真实案例；人工 UAT
   和 mock-only UAT 只能作为辅助发现问题，不能作为最终完成证据。
   真实案例不等于所有 domain adapter 都必须接真实系统；adapter 真/假服从当前
   spec 边界。但当 spec 要求 live LLM 时，模型路径必须是真实外部 LLM，不能用 mock
   或 deterministic provider 代替。

## 命令

- 优先用 `rtk` 包裹命令。
- 若 shell 找不到 `rtk`，先尝试 `/opt/homebrew/bin/rtk`。
- 不得因为 `PATH` 缺失就直接报告工具不存在。

## Frontend rem

前端视觉尺寸默认用 `rem`。除非已有测试 allowlist 或有明确设备像素理由，不得新增裸
`px`。

- 修改 `frontend/src/**/*.vue`、`frontend/src/**/*.css` 或视觉尺寸相关 TS 时，至少运行：
  `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
- slice 最终仍需跑完整前端单测。
- E2E/UAT 不替代 rem gate。

## 项目结构目标

```text
app/
  main.py
  core/
  modules/{provider,agent,chat,knowledge,workflow,mcp}/
tests/{unit,integration,contract,e2e}/
specs/
```

## 执行顺序

1. `000-current-boundary-inventory`
2. `001-backend-foundation`
3. `002-frontend-foundation`
4. `003-provider-management`
5. `004-agent-management`
6. `005-chat-engine`
7. `006-knowledge-mock-replica`
8. `007-workflow-replica`
9. `008-mcp-replica`
10. `009-real-rag-pgvector`
11. `010-real-tool-calling-and-mcp`

边界不清时，先更新 `000-current-boundary-inventory` 和 ADR，再继续。

## Slice 门禁

每个 slice 必须有证据：

- RED：新增或修改测试，按预期失败。
- Unit：相关单测全绿。
- Integration/Contract：接口、数据库或跨模块行为全绿。
- E2E：关键用户路径自动化验证全绿。
- Browser UAT：真实浏览器验证用户可见结果；涉及用户流程时必须有可重复脚本或
  明确的内置浏览器自动化步骤。
- Real-case UAT：涉及外部 LLM、真实业务 API、真实 adapter、真实数据流或生产评估
  价值时，必须走真实服务/沙箱/contract-backed live service。缺少 key、预算、网络、
  测试数据或 sandbox 时，门禁状态只能是 blocked / waiting-human，不能 PASS 或静默
  skip。
  若当前 spec 明确 domain adapter 只做 mock/seam，则真实案例 UAT 可以使用该 mock
  adapter；但 live LLM 要求一旦列入验收，模型调用必须是真实外部 provider。
- Frontend rem：涉及前端视觉尺寸时 rem gate 和完整前端单测全绿。
- Docs：`spec.md` / `plan.md` / `tasks.md` 状态和证据链接更新。

证据目录：

```text
artifacts/slices/{spec-id}/{slice-id}/
  red.txt
  unit.txt
  integration.txt
  e2e.txt
  uat.md
  screenshots/
```

## Loop 约束

本项目的 loop 是“有界 slice -> 验证 -> 评审 -> 记录 -> 下一 slice / 停止”。
具体运行细节放在 `loop/README.md`。

- 默认可在同一个 active spec 内连续推进已定义 slice。
- 用户要求 `single-slice`、完成后停止或等待确认时，必须停止。
- 不得自动新增 slice、重排 slice、扩大 active spec 范围。
- 不得弱化、删除、跳过测试、verifier、spec 或门禁。
- 不得在没有 checker 输出和证据时声称成功。
- 不得覆盖用户已有的无关改动。

停止条件：

- 达到 5 轮上限。
- 同一失败连续两轮出现。
- 修复导致之前通过的检查失败。
- 连续两轮失败项数量没有减少。
- 功能边界变化但缺少对应 `spec.md`、`plan.md`、`tasks.md` 或 RED 证据。
- 需要新增依赖、架构改动、公共 API / 数据模型改动、权限、生产、发布、真实数据、
  外部动作或不可逆操作，且缺少用户确认。
- 阻塞原因涉及当前仓库无法解决的外部依赖、密钥、服务、浏览器 UAT 条件或数据库环境。

触发停止条件时，只允许补充只读证据、更新 `loop/STATE.md` / `loop/LESSONS.md`，
并向用户报告当前轮次、失败项、已尝试修复、已通过检查和推荐选项。
