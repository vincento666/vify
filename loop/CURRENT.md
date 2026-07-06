# Current Loop Scope: AI Assistant General Harness MVP

## Status

Active implementation sprint:

```text
222.13 Tool Observation Self-Correction Correction (pending-confirmation)
```

Pending confirmation:

```text
222.14 Production Hardening Backlog
```

This file is the spec-facing loop pointer. Other loop engineering files such as
`loop/STATE.md` and `loop/VERIFIERS.md` are operational sprint artifacts; they
must not become alternate spec sources of truth.

## Active Spec

Spec id:

```text
222-ai-assistant-general-harness-mvp
```

Spec files:

```text
specs/222-ai-assistant-general-harness-mvp/spec.md
specs/222-ai-assistant-general-harness-mvp/plan.md
specs/222-ai-assistant-general-harness-mvp/tasks.md
```

Working title:

```text
AI Assistant General Harness MVP
```

## Completed Sprint

`222.8 SkillRuntime` is complete.

```text
Added first-class SkillRuntime discovery and metadata indexing, progressive
SKILL.md loading after trigger match, on-demand references/scripts/assets
reads, version/checksum/risk metadata, ToolRuntime-backed skill tools, and
skill load/resource audit events.

`run_skill_script` is exposed as a high-risk planning path through the existing
PermissionPolicy/ToolRuntime gate. It does not execute real external scripts in
the MVP path before approval.
```

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/reviewer-round1.md
```

## Current Sprint

`222.11 Live LLM Real-Case UAT` is complete.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-llm-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-realistic-cases-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/audit-export-redacted.json
```

`222.12 Real-Time Streaming And Durable Worker Correction` is complete after
Checker round4 and Reviewer round4 PASS.

On 2026-07-05, the MVP boundary was corrected: realistic cases must be proven
through an external live LLM UAT path. The civil-aviation adapter boundary
remains the original mock adapter seam. `222.11` is now the next defined slice.

On 2026-07-06, a gap review found that the spec goal is broader than the
current evidence for streaming, durable workers, and tool self-correction.
Human provided an OpenRouter runtime secret path during the 2026-07-06 loop.
OpenRouter `/models` confirmed the target slug `qwen/qwen3.6-27b`; the key
remained runtime-only and redacted, with conservative live UAT limits.

Reason:

```text
Deterministic local UAT is no longer sufficient for final MVP completion. The
harness remains generic, and final acceptance must prove realistic cases
through a real external model path.
```

Completed 222.9 reviewer-fix:

```text
Reviewer round1 found false-PASS risk in the eval gate and incomplete runtime
budget/model-degradation wiring. Human selected option `A` for a targeted fix.
Checker round2 and Reviewer round2 passed.
```

Implementation boundary:

```text
222.11 did not add real civil-aviation integrations or aviation branches to
the generic harness kernel. Aviation behavior remains limited to the mock
`BusinessToolAdapter` implementation and policy configuration. The live LLM
gate used OpenRouter `qwen/qwen3.6-27b` with runtime-only secret injection,
small capped UAT runs, and redacted audit artifacts.
```

Latest 222.11 preflight:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/preflight.md
```

Reviewer round1 resolution:

```text
Reviewer round1 found that the aggregate evaluator could false-pass on
synthetic evidence, the required aggregate-production-report.md artifact was
missing, and the Docs Gate remained open. Human selected option `A`; the
targeted reviewer-fix now grounds aggregate production evaluation in real
222.10 artifacts, workspace source assertions, docs state, UAT evidence, and
`aggregate-trace-audit-export.json`. Checker round2 and Reviewer round2 passed.
```

## Non-Goals

Out of scope for the next sprint unless separately approved:

```text
making `memory.md` mandatory
new dependency
database schema or migration change
public API contract change outside the 222.11 confirmed preflight contract
real civil-aviation API, airline system, rule, credential, or integration
committing provider keys, airline credentials, customer PII, or secrets
real external skill script execution
unapproved AGENTS.md writes
frontend redesign beyond TraceAuditEvalBudget visibility required by tests
new runtime job table or external broker
```

## Continuous Slice Mode

Slice advance mode:

```text
continuous within active spec unless a human gate or stop rule fires
```

222.10 has passed RED, implementation, self-gates, independent Checker round2,
independent Reviewer round2, artifacts, and docs gates for the previous
aggregate boundary. 222.11 is now proceeding after its real external-service
preflight contract was frozen for OpenRouter `qwen/qwen3.6-27b` and realistic
mock aviation cases.

The human confirmed the 2026-07-06 corrective spec update, so loop execution may
advance through `222.12` without weakening the `222.11` live LLM gate. This is
not a silent reorder; it is a confirmed corrective slice for internal P0 runtime
gaps that can be worked locally before the live-provider contract is available.

## Stop Conditions

Stop and enter `waiting-human` if the next sprint requires any of:

```text
unknown live LLM provider/model/key/budget
unknown realistic case set
making `memory.md` mandatory
new dependency
database schema or migration change
public API contract change outside the confirmed 222.11 preflight boundary
permission, sandbox, billing, secret, production, or external-service behavior
real AGENTS.md mutation without approval-gated contract semantics
real civil-aviation API, airline system, rule, credential, or integration
weakening or deleting tests/gates/checkers
unclear or non-objective acceptance criteria
same verifier failure for two rounds
Reviewer or Checker reports evidence gaps, scope expansion, or gate bypass
```

## 222.11 Runtime Contract

Confirmed:

```text
provider: OpenRouter
base URL: https://openrouter.ai/api/v1
model: qwen/qwen3.6-27b
credential path: runtime-only OPENROUTER_API_KEY injection; do not persist
budget: small scripted UAT with capped maxTokens; stop on quota/rate/provider errors
realistic cases: refund, change ticket, baggage, flight disruption through mock aviation seam
redaction: no raw API key, secrets, or real airline/customer PII in artifacts
```
