# Hify Python 迁移协作规范

本仓库的当前目标是把 `socutes/hify` 现有功能边界换壳复刻到
`Python 3.12 + FastAPI + SQLAlchemy 2.0` 技术栈。迁移不是直接翻译 Java
文件，而是按原项目从 0 到 1 的阶段顺序，使用 Spec Kit + TDD 逐 slice
推进。

## 不可变原则

1. **先复刻，后增强**：`001` 到 `008` 只复刻当前已有功能边界和 Mock 行为；
   真实 pgvector RAG、真实 tool calling、真实 MCP 强化放到 `009` 和 `010`。
2. **API 兼容优先**：前端仍使用 `/api/v1/...`，响应 envelope 保持
   `{code, message, data}`。
3. **Python 版本固定**：运行时固定 Python 3.12，`requires-python` 使用
   `>=3.12,<3.13`。
4. **Spec 先行**：每个 feature 必须先有 `spec.md`、`plan.md`、`tasks.md`，
   再实现。
5. **TDD 强制**：每个 slice 必须先写红测并保存失败证据，再写最小实现。
6. **门禁串行**：一个 slice 未通过全部门禁，不得进入下一个 slice。
7. **浏览器 UAT 必须执行**：凡影响前端或用户流程的 slice，必须用真实浏览器
   验证并保存截图/记录。

## Frontend rem 规范

前端视觉尺寸必须以 `rem` 为默认单位，保持全局缩放、浏览器字号和不同视口下
的一致性。除非已有测试明确 allowlist，否则不得在 Vue/CSS 中新增裸 `px`。

- **禁止裸 `px`**：宽高、间距、边框圆角、阴影偏移、字体大小、图标尺寸、
  固定定位偏移等视觉尺寸必须使用 `rem`，例如 `1px` 写为 `0.0625rem`。
- **允许的例外必须可解释**：确实依赖设备像素、canvas/SVG 内部坐标、
  第三方库要求、或测试 allowlist 的场景，必须局部说明原因，不能顺手使用。
- **前端改动必须跑 rem 门禁**：凡修改 `frontend/src/**/*.vue`、
  `frontend/src/**/*.css`、或视觉尺寸相关 TS，至少运行
  `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；
  slice 最终门禁仍需跑完整 `test:unit`。
- **新增样式先查单位**：提交前用 `rg "px|rpx|vw|vh"` 等方式快速扫新增样式，
  裸 `px` 必须改成 `rem` 或补入明确 allowlist。
- **E2E/UAT 不替代 rem 门禁**：浏览器看起来正常不代表缩放治理通过，必须以
  `remScaleClosure` 和完整前端单测结果为准。

## 项目结构目标

```text
app/
├── main.py
├── core/
├── modules/
│   ├── provider/
│   ├── agent/
│   ├── chat/
│   ├── knowledge/
│   ├── workflow/
│   └── mcp/
tests/
├── unit/
├── integration/
├── contract/
└── e2e/
specs/
├── 000-current-boundary-inventory/
├── 001-backend-foundation/
└── ...
```

## Slice 验收门禁

每个 slice 必须完成以下证据：

- **RED**：新增或修改测试，运行后按预期失败，保存失败输出。
- **Unit**：相关单测全绿。
- **Integration/Contract**：接口、数据库或跨模块行为全绿。
- **E2E**：关键用户路径自动化验证全绿。
- **Browser UAT**：真实浏览器手工或 Playwright 验证用户可见结果。
- **Frontend rem**：涉及前端视觉尺寸时，`remScaleClosure` 和完整前端单测必须全绿。
- **Docs**：`spec.md`/`plan.md`/`tasks.md` 状态更新，记录完成证据。

推荐证据目录：

```text
artifacts/slices/{spec-id}/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
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

任何阶段发现边界不清，先更新 `000-current-boundary-inventory` 和 ADR，再继续。

## Loop Engineering Stop Rules

本项目支持 Loop Engineering 工作流：`builder` 负责实现/修复，`checker` 只运行检查并报告失败，编排器最多循环 5 轮。循环仍必须服从本文件的 Spec Kit、TDD、slice 门禁、浏览器 UAT、Frontend rem 和 `rtk` 命令规范。

循环在以下任一条件成立时停止：

1. `ALL GREEN`：所有相关检查通过，并附上逐项通过证明。
2. 达到 5 轮上限。
3. 同一失败连续两轮出现。
4. 修复导致之前通过的检查失败。
5. 连续 2 轮失败项数量没有减少。
6. 功能边界变化但缺少对应 `spec.md`、`plan.md`、`tasks.md` 或 RED 证据。
7. 失败原因涉及当前仓库内无法解决的外部依赖、密钥、服务、浏览器 UAT 条件或数据库环境。

红线：不得弱化、删除、跳过测试或检查；不得修改 checker 工具白名单；不得在没有 checker 输出时报告成功；不得覆盖用户已有的未相关改动。

停止并升级时必须报告当前轮次、仍失败项、已尝试修复、已通过检查，以及为什么继续循环不会解决问题。
