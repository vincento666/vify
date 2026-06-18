# Browser UAT: AI Assistant Event Echo UX

Date: 2026-06-18

Model path:
- Provider: OpenRouter
- Model: `qwen/qwen3.5-27b`
- Temporary API key used only through the runtime UI field; not persisted in source or artifact text.

Journey:
1. Opened `/ai-assistant` in a real Chromium browser.
2. Created a new AI Assistant session.
3. Configured model runtime for OpenRouter `qwen/qwen3.5-27b`.
4. Sent a complex Chinese harness UAT prompt requiring:
   - read `AGENTS.md`;
   - read `specs/193-ai-assistant-live-orchestration-mvp/spec.md`;
   - plan a write;
   - wait for approval;
   - approve the write through the UI;
   - write `browser-uat-write.txt`.
5. Expanded the completed run task and every nested event card.
6. Replayed the persisted run after the thought-dedup fix without another model call.

Observed run evidence:
- Run id: 13
- Events persisted: 100
- Read tools completed: 2
- Write tool completed: 1
- Approval clicked in UI: true
- Generated file: `artifacts/slices/193-ai-assistant-live-orchestration-mvp/slice-ui-event-echo-ux/browser-uat-write.txt`

Final UI checks after replay:
- Page body scroll: false
- Left run-row selector present: false
- Global stream toggle selector present: false
- Run task cards: 1
- Event cards: 25
- Model output segments: 2
- Thought summaries: 0
- Duplicated thought summaries: 0
- Tool input detail anchors: 4
- Tool output detail anchors: 4
- Running node spinners after completion: 0
- Usage units: `输入 tokens`, `输出 tokens`, `总计 tokens`, `耗时 ms`
- Generic `里程碑` copy present: false
- Generic `动态事件` copy present: false
- `运行记录` copy present: false

Screenshots:
- `screenshots/uat-before-run.png`
- `screenshots/uat-running.png`
- `screenshots/uat-expanded-final.png`
- `screenshots/uat-replay-deduped.png`

Remaining risk:
- The browser UAT succeeded against the running dev stack, but repository-level MySQL8 integration/e2e gates remain blocked by database INDEX privilege.

