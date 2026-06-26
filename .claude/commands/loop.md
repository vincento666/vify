---
description: 循环运行 builder 和 checker，直到 Hify 检查通过或触发停止规则
argument-hint: <task>
allowed-tools: Read, Grep, Glob, Bash, Task
model: sonnet
---

以 Loop Engineering 方式执行此任务：$ARGUMENTS

## 第 0 步：对齐目标

写一行任务简报，包含：

- 目标
- 预计涉及文件
- 完成标准
- 需要满足的 Hify slice/Spec Kit/TDD 门禁

把这行任务简报原样传给 builder 和 checker。

## 循环

1. 声明 `Cycle N/5`。
2. 派 `builder` 实现任务，或修复上一轮 checker 失败报告。
3. 派 `checker` 运行相关检查。
4. 如果 checker 输出 `ALL GREEN`：停止，向用户展示 diff 摘要和逐项检查结果。
5. 如果 checker 输出 `FAILED`：把 checker 的完整失败报告原样转发给 builder，不要解读、压缩、过滤或改写。
6. 回到第 1 步。

## 轮次管理

- 最多 5 轮。
- 同一失败连续出现两轮时停止。
- 修复导致之前通过的检查失败时停止。
- 连续 2 轮失败项数量没有减少时停止。
- 如果发现缺少 spec/slice、环境依赖、密钥、外部服务或浏览器 UAT 条件，且无法在当前仓库内解决，停止并升级给用户。

## Hify 特别规则

- 所有 shell 命令都以 `rtk` 开头。
- 不要跳过 RED 证据、Unit、Integration/Contract、E2E、Browser UAT、Docs 等 slice 门禁。
- 前端视觉尺寸改动必须执行 rem 门禁。
- 不修改用户已有的未相关改动。

停止条件和升级协议以项目根目录 `CLAUDE.md` / `AGENTS.md` 的 Loop Engineering stop rules 为准。
