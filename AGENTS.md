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
