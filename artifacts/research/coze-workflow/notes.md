# Coze Workflow Canvas Reference Notes

## Browser Access

- Direct Coze platform access: `https://www.coze.com/`
- Evidence: `coze-home-1440.png`
- Result: page reached through Chromium, but the first unauthenticated capture stayed in a loading state.

## Current In-App Browser Visual References

- Current source URL opened by the user in Codex in-app Browser: `https://www.coze.cn/work_flow?workflow_id=7639360865686634515&space_id=7392442439686553619`
- Full desktop evidence captured on 2026-06-01: `coze-iab-desktop-20260601.png`
- User-provided in-app Browser panel screenshots on 2026-06-01 show the current Coze LLM node configuration panel and are authoritative for LLM panel structure.
- This current authenticated `coze.cn` canvas is the implementation reference for spec 011/012 visual work.
- Browser automation note: later in-app Browser automation succeeded for targeted screenshots and interactions; the current audit artifact supersedes earlier timeout-only evidence.

## Historical Public Visual References

- Source page archived locally: `chloevolution-coze-workflow.html`
- Key canvas image: `coze-workflow-node_hu_503fa31c1fa4b206.png`
- Additional interaction references:
  - `google-web-search-plugin_hu_25e5901901364e44.png`
  - `google-web-search-plugin-settings_hu_155521dcc67dc565.png`
  - `run-test-result-example_hu_a4136a4cf9c7fee8.png`
  - `code-node-settings_hu_c0189fbcd6f83c96.png`
  - `llm-node-settings_hu_eb64901f44dbc0a8.png`

The public article screenshots are historical and must not be used as the pixel target when they conflict with the current in-app Coze canvas.

## UI Observations To Reuse

- Header shows back navigation, app icon, flow name, status badge such as `已自动保存`, and a light workspace strip.
- Header right side shows compact action icons, a primary purple `发布` button, and a more menu.
- The current live reference has no top product banner; do not reserve banner height unless a newer live reference reintroduces one.
- Canvas uses a subtle dotted grid with white rounded node cards and small purple side ports.
- Current authenticated deep link uses the `/work_flow` route and displays shared Workflow/Chatflow canvas chrome. Start input pills include `USER_INPUT`, `CONVERSATION_NAME`, and an overflow `...` chip.
- Current graph shows compact `开始`, `大模型`, and `结束` cards; `结束` can sit partly outside the visible right edge.
- Node cards are flatter than the historical screenshots: icon + title header, compact input/output rows, and pill variables.
- Selected node uses a bright purple outline; ports are filled purple circles on left/right middle edges. The selected LLM card shows compact row summaries: `输入 str.input`, `输出 str.output str.abc str.cde`, model row, and skill row.
- Clicking a node selects it with a purple outline and opens a right-side configuration panel with collapsible sections such as input, model/prompt body, and output.
- Bottom toolbar is centered near the lower edge with panel/view control, zoom dropdown, compact utility icons, a prominent `+ 添加节点` button, a `角色` button, a wrench/tools icon, and a green `试运行` button.
- The current live reference does not expose an operation-mode toggle. Hify keeps a visible operation-mode icon button as a deliberate product override; the button exposes `触控板模式` / `鼠标模式` through tooltip/aria label and must switch the canvas control mode.
- Wrench/tools icon opens or toggles a bottom docked debug/tools panel. The panel can host error list, run diagnostics, logs, or other canvas diagnostics without replacing the right-side node config panel.
- Bottom left/bottom dock can show a docked `错误列表` panel with empty-state illustration and close action.
- Full-flow debug/result opens as a bottom docked `调试` panel with run tree, `详情` flamegraph/detail area, close action, and sticky green `保存并开始对话调试`. A right-docked Chatflow input drawer was not confirmed in the latest live audit.

## LLM Node Panel Observations

- Panel header shows node icon, title `大模型`, run icon, more menu, close icon, and description `调用大语言模型,使用变量和提示词生成回复`.
- LLM has a segmented mode control: `单次` and `批处理`. Current MVP only implements `单次`; `批处理` is out of scope.
- `模型` section has model selector, info icon, dropdown affordance, and settings gear. The selector value is visible on both panel and node card.
- Model selector opens a large popover with title `模型选择`, info icon, search icon, and Coze-like model rows with logo, model name, short description, and capability tags. Hify should replace Coze source tabs with internal enabled Provider/model groups from spec 003, such as configured provider names and their enabled model configs.
- Model settings gear opens a large settings popover with protocol tabs (`Chat Api`, `Responses Api`), generation diversity presets, length sliders/inputs, model default instruction toggles, and deep-thinking controls. These are reference for later advanced model-parameter work, not current MVP implementation.
- `技能` section has an add button and empty state `暂未配置技能`. MVP can expose the shell while leaving real skill/plugin configuration out of scope.
- In Hify, the Coze `技能` section should map to a Unified Resource selector. Knowledge Bases, MCP tools, and subworkflows can share picker styling, but runtime support is staged: Knowledge can become LLM context first; MCP tools and subworkflows need later execution contracts.
- `输入` section has a `会话历史` toggle in Chatflow context, add button, variable name column, variable value column, type selector (`str.`), upstream variable chip such as `开始 - USER...`, selector/action icon, and delete action.
- Variable reference picker opens as a compact cascading popover. First level groups include `用户变量`, `应用变量`, `系统变量`, and connected upstream node groups such as `开始`; selecting/hovering a source opens a second panel listing variables such as `USER_INPUT`, `CONVERSATION_NAME`, and custom start variables, each with type badges.
- `视觉理解输入` exists in Coze but is out of scope for current MVP.
- `系统提示词` is a large editor section with utility icons for prompt helpers, variable/tools/library-like actions, expand, and AI assist. It accepts direct text.
- `用户提示词` is a separate editor below system prompt. Placeholder documents manual reference syntax: `{{变量名}}`, `{{变量名.子变量名}}`, and `{{变量名[数组索引]}}`.
- `输出` section has output format selector (`文本`, `Markdown`, `JSON`), helper/import-style action, add action, variable name rows, variable type dropdown rows, expand/detail action, and delete action.
- `支持续写` and `异常处理` exist in Coze but are out of scope for current MVP.

## Single-Node Test Drawer Observations

- Clicking the LLM panel header run icon opens an inner right-panel drawer over the config content while the parent node header remains visible behind it.
- Drawer idle state:
  - Header title `试运行`, optional `查看日志`, and close icon.
  - Body starts with `试运行输入`.
  - Right side has `JSON模式` toggle and purple split button `AI 补全` with dropdown arrow.
  - Each required test input row shows variable name and type badge, such as `input` + `String`, followed by an input box.
  - Sticky bottom action is a full-width green `运行` button with play icon.
- Running state:
  - Parent node header run icon changes to stop-like state.
  - Drawer body centers a spinner and text `试运行进行中...`.
  - Sticky bottom action changes to grey `停止` button.
- Success state:
  - Drawer header shows a green success pill with check icon, elapsed time and token usage such as `7s | 460 Tokens`, plus `查看日志`.
  - `试运行输入` keeps the last input values.
  - `运行结果` contains sections for `输入`, `推理内容`, `技能调用`, and `输出`, each using bordered output boxes and copy affordances where applicable.
  - `推理内容` is the model-visible response/debug text returned by the node execution, not hidden chain-of-thought.
  - `技能调用` is empty when no skill/resource/tool was invoked.
  - `输出` displays parsed output variables such as `output`, `abc`, and `cde`.
  - Sticky bottom action returns to green `运行` for rerun.
- Failure state was not captured, but should mirror success layout with a red status pill and error details in the result area.

## Official Coze Resource And Skill Vocabulary

Research date: 2026-06-01.

- Official Coze/Coze Studio pages are JS-rendered, so the exact SaaS document body for `llm_node` was not extractable through plain HTML. Sources used here are the official Coze docs URLs, the official Coze Studio GitHub/Wiki pages, and public Coze web bundle strings loaded by the current docs/product pages.
- Coze Studio README defines `workflows`, `plugins`, `databases`, `knowledge bases`, and `variables` as resources. This supports Hify using a broad "Unified Resource" product language.
- Coze official plugin configuration says plugin tools extend LLM capability by searching the internet, scientific calculation, drawing images, etc., and let LLMs connect to the external world. It also distinguishes "Add Plugins to an Agent" from "Select Plugins for Workflow Plugin Nodes".
- Coze workflow backend docs say a workflow node belongs to a node type such as large model node or plugin node. Therefore an LLM node and a plugin node remain different workflow node types even when the LLM prompt editor exposes a `技能` affordance.
- Official Coze web bundle strings for workflow nodes define:
  - `wf_node_plugin_node_desc`: `通过添加工具访问实时数据和执行外部操作`
  - `wf_node_wf_node_desc`: `集成已发布工作流，可以执行嵌套子任务`
  - `workflow_knowledge_node_empty`: `请添加知识库到此节点`
  - `workflow_prompt_editor_skill`: `技能`
- Official Coze web bundle strings for Chatflow/Agent skills expose:
  - `chatflow_agent_skill_knowledge_tooltip`: `知识库`
  - `chatflow_agent_skill_tool_tooltip`: `插件`
  - `chatflow_agent_skill_workflow_tooltip`: `工作流`
  - `chatflow_agent_skill_imageflow_tooltip`: `图像流`
- Official analytics copy says triggered Agent skills refer to plugins and workflows when building an Agent. Knowledge appears as a separate message/trace type (`knowledge`) and as a selectable skill-like item in Chatflow UI, so do not collapse all skill types into a single runtime behavior.
- Hify implication: keep the Coze-like `技能` section visually, but model it as a typed resource selector with explicit support states:
  - Knowledge: can be implemented first as retrieved LLM context.
  - Plugin/MCP tool: later LLM tool-calling runtime.
  - Workflow/subworkflow: later nested execution runtime.
  - Imageflow: Coze capability, out of current Hify MVP.

## Implementation Boundary

- Spec 011.1 only establishes module tabs and route shell.
- Spec 011.2 starts the canvas replica using `spec-011-015-live-audit-20260601.md` and its screenshots as the primary visual target for shared canvas chrome, node cards, ports, edges, toolbar, add-node menu, and bottom debug dock.
- Spec 012 uses the same live audit for Chatflow system input variables and conversation-shaped debug/run behavior.

## Live Audit Correction 2026-06-01

The authenticated in-app browser was re-run against:
`https://www.coze.cn/work_flow?workflow_id=7639360865686634515&space_id=7392442439686553619`.

New primary audit:
`artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`.

Corrections that supersede older notes when there is a conflict:

- The current visible bottom toolbar does not expose an operation-mode toggle, but Hify requires a visible operation-mode icon button in the bottom toolbar as a product override. The mode names belong in tooltip/aria labels, not visible toolbar text.
- The current live full-flow debug/result surface is a bottom dock titled `调试`, with run tree, detail/flamegraph area, close action, and sticky `保存并开始对话调试`.
- The current live audit did not confirm a standalone right-docked Chatflow input drawer. Chatflow specs should require conversation-shaped input/profile behavior but use the bottom debug dock for result evidence unless a newer live capture proves otherwise.
- The add-node menu is a bottom-toolbar popover with search and grouped entries: `大模型`, `插件`, `工作流`, `代码`, `选择器`, `意图识别`, `循环`, `批处理`, `变量聚合`, `异步任务`, `输入`, `输出`, `SQL自定义`, `新增数据`, `更新数据`, `查询数据`, `删除数据`, `知识库写入`, and `知识库检索`.
