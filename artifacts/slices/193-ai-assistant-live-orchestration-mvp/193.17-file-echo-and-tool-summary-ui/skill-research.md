# Skill And Tool Echo Research

Local finding:

- `invoke_skill` is a real AI Assistant Harness tool in
  `app/modules/ai_assistant/domain/tools.py`.
- It records skill intent and returns `skillName`, `instruction`, and
  `status: RECORDED`.
- It does not execute local Codex `SKILL.md` workflows inside this app.
- The live model prompt in `app/modules/ai_assistant/domain/live_model.py`
  explicitly tells qwen to use `invoke_skill` when the user mentions TDD,
  testing, code review, debug, skill, or specs.
- Therefore `skill=tdd` was not random hallucination. It was a raw rendering
  artifact from our previous UI formatting, now replaced with `使用技能`.

External product notes:

- OpenClaw describes tools as callable actions and skills as workflow
  instructions. Tool execution and skill loading are distinct product concepts:
  https://docs.openclaw.ai/tools and https://docs.openclaw.ai/tools/skills
- Hermes skills are on-demand knowledge documents loaded when relevant:
  https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Claude Agent Skills are modular capabilities with instructions and resources
  selected when relevant:
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- OpenAI Codex CLI emphasizes watching plans and actions as they happen:
  https://developers.openai.com/codex/cli/features
- Windsurf/Cascade exposes tools such as search, analysis, web search, and
  terminal, while limiting calls per prompt:
  https://docs.devin.ai/windsurf/plugins/cascade/cascade-overview
- Cursor CLI presents shell command execution with safety checks and output:
  https://cursor.com/cli

Design decision:

- File read/write/create calls should not be shown as generic tool calls. They
  are rendered as top-level file echo nodes (`已读取/已编辑/已创建 N 个文件`) with
  structured path/result details.
- Non-file tools remain in one summarized tool echo per contiguous segment,
  with Chinese input/output rows and no raw `skill=tdd` display.
