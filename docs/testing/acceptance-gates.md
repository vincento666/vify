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

## 6. Docs Gate

目的：让规格文档和真实实现同步。

要求：

- 更新对应 `spec.md` slice 状态。
- 更新 `tasks.md` 完成项。
- 如发生架构决策变化，新增或更新 ADR。

## Slice Done 定义

一个 slice 只有在以下条件都满足时才算完成：

- RED 证据存在。
- Unit 通过。
- Integration/Contract 通过。
- E2E 通过或有明确“不涉及 UI”的记录。
- Browser UAT 通过或有明确“不涉及 UI”的记录。
- 文档状态已更新。
