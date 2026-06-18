# 193.3 Browser UAT

Date: 2026-06-18
Target: `http://127.0.0.1:5173/ai-assistant`
Model: OpenRouter `qwen/qwen3.5-27b`

## Journey

1. Opened `/ai-assistant` in a real Chromium browser against the running Vite
   frontend and FastAPI backend.
2. Created a new AI Assistant session.
3. Entered a temporary OpenRouter key in the model config field without
   persisting or echoing it.
4. Sent: "请先使用工具读取 AGENTS.md，然后根据读取内容用一句中文说明本仓库 AI 助手协作规范；不要写入任何文件。"
5. Observed live run events, then waited for completion.
6. Reopened the completed run group and expanded an event detail panel.

## Evidence

- Final run status: `COMPLETED`.
- Persisted event stream included:
  `run.started`, `orchestration.phase_started`, first `model.call_started`,
  first `model.stream_chunk`, `model.tool_call_decision`,
  `scheduler.batch_started`, `tool.call_started`, `tool.call_output`,
  `tool.call_completed`, `scheduler.batch_completed`, second
  `model.call_started`, 22 more `model.stream_chunk` events,
  `model.tool_call_decision`, `model.call_completed`, `run.completed`.
- Tool calls: `read_workspace_file`.
- `model.stream_chunk` persisted events: 23.
- Expected visible model output groups after consecutive-chunk assembly: 2.
- Browser DOM visible model output cards after expanding run group: 2.
- Browser DOM milestone count after expanding run group: 21.
- Browser DOM detail rows after expanding one event: 4.
- Whole-page scroll: none (`scrollHeight == clientHeight == 900`).
- Composer remained inside viewport (`composerBottom 873.609375 <= 900`).
- Screenshot:
  `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.3/screenshots/ai-assistant-run-event-group-uat.png`

## Verdict

Pass for this slice:

- Completed runs are collapsed by default.
- Expanding the run shows a single task group with a milestone execution line.
- Clicking an event expands formatted nested detail rows.
- Model output is displayed as stream segments, not one UI card per raw chunk.
- Tool echo and second model output are interleaved in persisted event order.
