# Tasks 188: AI Assistant Prompt Skills Memory Compaction

## 188.0 Documentation Sign-Off

- [x] Create `188-ai-assistant-prompt-skills-memory-compaction`.
- [x] Record that 184 originally reserved Phase 5 as spec id 186 and that this
      repository now uses 188 as the requested collision-free id.
- [x] Limit this spec to PRD Phase 5 prompt, skills, memory, and compaction.
- [x] Declare backend-first scope with no frontend visual changes.
- [x] Declare MySQL8-only persistence and test evidence.
- [x] Declare deterministic/no live LLM behavior by default.
- [x] Declare OpenRouter as optional, env-gated, skipped by default, and
      credential-free in repo artifacts.
- [x] Declare read-only skill registry scope with no dynamic skill execution.
- [x] Declare working memory persistence via existing AI Assistant storage or
      JSON context first.
- [x] Declare compaction summary persistence and deterministic generation.
- [x] Declare that customer-assistant dirty files are out of scope.
- [x] Save planning evidence under
      `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.0/`.

## 188.1 Domain Prompt Tracer

- [x] RED: unit tests fail because `PromptMemoryItem` and `SkillRegistry` do
      not exist.
- [x] Add read-only `SkillRegistry` and `SkillManifest`.
- [x] Add deterministic memory item prompt rendering.
- [x] Add optional project instructions and compaction summary layers.
- [x] Preserve 184 default prompt layer order when optional inputs are absent.
- [x] Run focused unit, ruff, mypy, AI Assistant kernel regression, and MySQL8
      boundary scan.
- [x] Save evidence under
      `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.1/`.

## 188.2 Prompt, Skills, Memory, And Compaction Backend Persistence MVP

- [ ] RED: unit tests fail for required prompt layer order beyond the 188.1
      domain tracer.
- [ ] RED: unit tests fail for read-only skill registry listing and deterministic
      skill activation in harness context.
- [ ] RED: MySQL8 integration tests fail for working memory persistence and
      reload.
- [ ] RED: MySQL8 integration tests fail for compaction summary persistence and
      reload.
- [ ] RED: contract tests fail for safe prompt layer, skill, memory, and
      compaction metadata in API/event/inspector payloads.
- [ ] RED: backend E2E fails because a later run does not yet receive persisted
      memory and compaction context.
- [ ] Extend prompt layer model and assembler order for persisted context:
      `base`, `project_instructions`, `skills`, `working_memory`,
      `compaction_summary`, `tools`, `run_state`, `user_message`.
- [ ] Implement read-only skill manifest model.
- [ ] Implement deterministic `SkillRegistry` listing and activation.
- [ ] Implement working memory item model.
- [ ] Persist working memory through existing AI Assistant JSON context if it
      satisfies MySQL8 replay requirements.
- [ ] Add an explicit `ai_assistant` memory schema only if JSON context is
      insufficient and evidence justifies it.
- [ ] Implement deterministic compaction summary model and generator.
- [ ] Persist compaction summary through existing AI Assistant storage where
      possible.
- [ ] Integrate project instructions, skills, memory, and compaction with the
      harness prompt path.
- [ ] Emit or expose safe prompt/memory metadata without hidden reasoning.
- [ ] Add optional `GET /api/v1/ai-assistant/skills` only if contract tests need
      a direct registry endpoint.
- [ ] Preserve scheduler, approval, sandbox, and proposed-action behavior.
- [ ] Keep default tests deterministic and credential-free.
- [ ] Keep optional OpenRouter checks env-gated and skipped by default.
- [ ] Run focused prompt/skills/memory unit, integration, contract, and E2E
      gates.
- [ ] Save evidence under
      `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.2/`.

## 188.3 Aggregate Backend Acceptance

- [ ] Rerun 188.1 and 188.2 focused gates.
- [ ] Rerun relevant 184 AI Assistant backend regressions for prompt, tool
      registry, security, inspector, and event replay.
- [ ] Rerun relevant 187 scheduler regressions for planned tool calls and
      scheduler metadata.
- [ ] Run MySQL8 boundary or focused SQLite scan for new prompt/memory tests.
- [ ] Run lint/type gates used by the existing AI Assistant backend.
- [ ] Confirm no frontend visual files changed.
- [ ] Confirm no `app/modules/customer_assistant/**` files changed.
- [ ] Record that browser UAT and remScaleClosure are not applicable because
      this backend-first slice does not alter frontend visuals.
- [ ] Save final evidence under
      `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.3/`.
- [ ] Update this task list only after evidence exists.
