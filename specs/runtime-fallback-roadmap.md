# Runtime Fallback Roadmap

## Numbering Audit

Checked on 2026-06-09.

The local `specs/` directory currently contains `000` through `042`.
The newest relevant runtime/knowledge sequence is:

- `033-runtime-fallback-policy`: runtime handoff and fallback control-plane
  foundation.
- `034-unified-routing-chat-lab`: unified routing chat lab and live acceptance
  surface.
- `035-knowledge-retrieval-productization`: productized knowledge retrieval,
  retrieval modes, FAQ embeddings, rerank, vector-store adapters, and runtime
  retrieval settings.
- `036-runtime-faq-exact-answer-gate`: runtime exact/high-confidence FAQ answer
  gate.
- `037-runtime-faq-embedding-answer-gate`: runtime semantic FAQ answer gate.
- `038-runtime-rag-answer-gate`: runtime RAG answer gate.
- `039-runtime-controlled-agent-fallback`: policy-controlled fallback Agent.
- `040-runtime-fallback-e2e-lab-acceptance`: full end-to-end and lab acceptance.
- `041-runtime-policy-config-observability`: backend policy profile, route
  parameter APIs, and decision-log observability.
- `042-runtime-policy-release-governance`: backend evaluation, release gate,
  canary, activation, and rollback governance.

`035` is already occupied by knowledge retrieval productization. Therefore the
remaining runtime fallback specs intentionally start at `036` and continue
through `040`. `041-042` then productize those runtime parameters for host
production-system operations without adding frontend UI.

## Implementation Order

1. Finish `033-runtime-fallback-policy`.
2. Implement `036-runtime-faq-exact-answer-gate`.
3. Implement `037-runtime-faq-embedding-answer-gate`.
4. Implement `038-runtime-rag-answer-gate`.
5. Implement `039-runtime-controlled-agent-fallback`.
6. Implement `040-runtime-fallback-e2e-lab-acceptance`.
7. Implement `041-runtime-policy-config-observability`.
8. Implement `042-runtime-policy-release-governance`.

This order preserves the agreed routing architecture:

```text
explicit safety/handoff triggers
  -> exact/high-confidence FAQ answer
  -> semantic FAQ answer
  -> constrained SOP/task intent arbitration
  -> RAG answer
  -> controlled fallback Agent
  -> human handoff
  -> policy profile config and decision logs
  -> evaluation-gated release and rollback
```

## SDD Boundary

The specs are intentionally isolated from direct Chatflow mutation until each
slice passes its own gate. Runtime fallback code may call existing modules
through ports/facades, but it must not rewrite Chatflow internals or knowledge
module internals while implementing 033 and 036-040.

`035` remains the knowledge provider boundary. `036-040` consume retrieval
results and policy evidence through runtime-lab contracts.

`041-042` are backend-only production embedding specs. They add operational
configuration, observability, evaluation, release, and rollback APIs for a host
system. They must not require Hify frontend configuration UI.

## TDD Rule

Every slice must follow the project gate:

- write RED unit/integration/contract tests first;
- save RED evidence under `artifacts/slices/{spec-id}/{slice-id}/red.txt`;
- implement the smallest runtime behavior needed to pass;
- save unit/integration/e2e evidence;
- update `spec.md`, `plan.md`, and `tasks.md` before the slice is signed off.

No slice may advance while the previous slice's route contract, evidence, and
task checklist are incomplete.

## Codex Goal Commands

Use these goals one by one.

### Goal 033

```text
请严格按照 specs/033-runtime-fallback-policy 的 spec.md、plan.md、tasks.md 完成 033.1-033.4。只实现 runtime-lab 的转人工/兜底控制面基础：新增 HANDOFF_TO_HUMAN 路由动作、显式转人工触发模板、handoff event/context snapshot、policy 回归门禁。必须 TDD 先红后绿，保存 artifacts/slices/033-runtime-fallback-policy 下的证据，不接入 FAQ/RAG/Agent，不改 Chatflow 内部实现，完成后更新 spec/plan/tasks 并提交 git。
```

### Goal 036

```text
请严格按照 specs/036-runtime-faq-exact-answer-gate 的 spec.md、plan.md、tasks.md 完成 036.1-036.3。实现 runtime-lab 的 ANSWER_FAQ exact/high-confidence FAQ answer gate，消费 035 的知识检索能力但不改知识模块内核；FAQ 高置信可在 SOP 意图仲裁前提前回答，active_sop 场景不得污染 SOP slot/state。必须 TDD+SDD，保存 RED/green/e2e 证据，完成后更新文档并提交 git。
```

### Goal 037

```text
请严格按照 specs/037-runtime-faq-embedding-answer-gate 的 spec.md、plan.md、tasks.md 完成 037.1-037.3。实现 runtime-lab 的 semantic FAQ answer gate，基于 035 的 faq retrieval mode、FAQ embeddings、score/margin/rerank evidence 做高置信问答；低置信或冲突必须交给后续 SOP 仲裁/澄清/兜底，不能绕过策略门禁。必须 TDD+SDD，保存证据并提交 git。
```

### Goal 038

```text
请严格按照 specs/038-runtime-rag-answer-gate 的 spec.md、plan.md、tasks.md 完成 038.1-038.3。实现 runtime-lab 的 ANSWER_RAG gate 和 RAG generator port，RAG 只处理咨询/长尾知识回答，必须带 citations/evidence，不得把 RAG 文档片段塞入 SOP intent classifier 候选，不得修改 active_sop slot/state。必须 TDD+SDD，保存证据并提交 git。
```

### Goal 039

```text
请严格按照 specs/039-runtime-controlled-agent-fallback 的 spec.md、plan.md、tasks.md 完成 039.1-039.4。实现 policy-controlled fallback Agent：Agent 只能在 PolicyGate 放行后回答、澄清、整理诉求或建议转人工；最终转人工动作仍由路由控制面执行，Agent 不得直接恢复/启动/挂起 SOP。必须覆盖澄清次数、低置信升级、handoff escalation 和 no task mutation 回归测试，保存证据并提交 git。
```

### Goal 040

```text
请严格按照 specs/040-runtime-fallback-e2e-lab-acceptance 的 spec.md、plan.md、tasks.md 完成最终验收。构建覆盖 handoff、exact FAQ、semantic FAQ、RAG、controlled Agent、clarification、active_sop safe answer、SOP continue/resume/switch、non-interruptible rejection 的真实 API + 后端高规格验收矩阵；必要时补 runtime-lab 前端证据，但不做新前端产品功能。必须输出预期/实际对比、完整 artifacts、最终能力审计，并提交 git。
```

### Goal 041

```text
请严格按照 specs/041-runtime-policy-config-observability 的 spec.md、plan.md、tasks.md 完成 041.1-041.4。目标是把 runtime-lab 路由参数从 env/demo wiring 提升为后端可配置的 RuntimePolicyProfile，并沉淀每次对话决策日志和当次使用的完整 policy snapshot。必须提供后端 API 支持宿主系统配置 classifier、FAQ/RAG 阈值、fallback Agent、handoff 等参数；不做前端；必须 TDD+SDD，保存 artifacts，更新 spec/plan/tasks，并按 slice 提交 git。
```

### Goal 042

```text
请严格按照 specs/042-runtime-policy-release-governance 的 spec.md、plan.md、tasks.md 完成 042.1-042.4。目标是为 RuntimePolicyProfile 建立后端评测、发布门禁、灰度、激活和回滚治理：activate 必须经过 profile validation、040 golden matrix replay、历史 decision logs replay、风险评估、审批和 rollback target 检查；不做前端；必须 TDD+SDD，保存 artifacts，更新 spec/plan/tasks，并按 slice 提交 git。
```

## Final Capability After 040

After all specs are complete, the runtime will support a controlled enterprise
customer-service dialogue stack:

- route-level human handoff can be triggered explicitly at any layer;
- FAQ exact/high-confidence answers can return before SOP arbitration;
- semantic FAQ answers can use embedding/rerank evidence without entering SOP;
- active SOP state is protected from FAQ/RAG/Agent answers;
- SOP entry, resume, suspend, and switch decisions still pass through
  constrained SOP/task arbitration when needed;
- RAG answers handle long-tail knowledge questions with citations and no task
  mutation;
- fallback Agent handles low-confidence tail cases, clarification, user
  reassurance, issue summarization, and handoff recommendation only after
  PolicyGate approval;
- repeated uncertainty can escalate to human handoff through control-plane
  policy, not through free-form Agent authority;
- final acceptance proves these behaviors through API, integration, E2E, and
  runtime-lab evidence.

## Final Capability After 042

After 041-042 are complete, the demo runtime can be embedded into a host
production system with backend-operable route governance:

- host systems can configure route parameters through backend APIs;
- classifier model, prompt, timeout, retry, fallback model, and minimum
  confidence can come from `RuntimePolicyProfile`;
- fallback Agent type, model/agent binding, prompt, knowledge bases, allowed
  response types, and max clarification attempts can come from
  `RuntimePolicyProfile`;
- FAQ/RAG thresholds and knowledge bindings are backend configurable;
- env remains bootstrap/default fallback only;
- every runtime decision stores final action, confidence signals, route
  evidence, and the exact policy snapshot used;
- candidate profiles can be evaluated against the 040 golden matrix and
  historical decision logs;
- activation is blocked unless validation, replay, risk, approval, and rollback
  gates pass;
- canary/active/rollback release records are auditable;
- host production systems can build their own operator frontend on these APIs.
