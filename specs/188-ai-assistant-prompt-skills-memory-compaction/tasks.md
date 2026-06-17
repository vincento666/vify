# Tasks 188: AI Assistant Prompt Skills Memory Compaction

## 188.0 Documentation Sign-Off

- [x] Create `188-ai-assistant-prompt-skills-memory-compaction`.
- [x] Record numbering collision with the original 184 roadmap ids.
- [x] Limit this spec to PRD Phase 5 prompt/skills/memory/compaction.
- [x] Declare backend-only deterministic MVP scope.
- [x] Declare real LLM tests deferred and OpenRouter environment-only.

## 188.1 Domain Prompt Tracer

- [x] RED: prompt tests fail because `PromptMemoryItem` and skill registry do
      not exist.
- [x] Add read-only `SkillRegistry` and `SkillManifest`.
- [x] Add deterministic memory item prompt rendering.
- [x] Add optional project instructions and compaction summary layers.
- [x] Preserve 184 default prompt layer order when optional inputs are absent.
- [x] Run focused unit, ruff, mypy, AI Assistant kernel regression, and
      MySQL8 boundary scan.
- [x] Save evidence under
      `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.1/`.

## Later Slices

- [ ] Add durable MySQL8 memory item persistence.
- [ ] Add API contracts for memory snapshots and compaction summaries.
- [ ] Add frontend presentation only if product shell requirements demand it,
      then run frontend unit, remScaleClosure, and browser UAT.
