# Tasks 193: AI Assistant Live Orchestration MVP

## 193.1 Live Model And Event Transport

- [x] RED: backend contract fails for `modelConfig` payload, streaming deltas,
      and SSE events.
- [x] Implement request schema and sanitized request hashing for `modelConfig`.
- [x] Implement OpenAI-compatible streaming client with delta accumulation.
- [x] Emit live stream chunks before model completion.
- [x] Add async message start and run event stream endpoints.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.1/`.

## 193.2 Product Shell Realtime UX

- [x] RED: frontend contract fails for model config controls, async API, stream
      helper, and no fixed toolName heuristic.
- [x] Add Chinese model configuration controls.
- [x] Remove frontend fixed tool selection.
- [x] Subscribe to AI Assistant SSE events per run.
- [x] Keep only the outer shell border.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.2/`.

## 193.3 ReAct Stream Assembly And Collapsible Run Timeline

- [x] RED: backend live contract fails until tool results are fed back into the
      second Qwen ReAct round.
- [x] RED: frontend shell contract fails until run echoes are grouped into a
      collapsible task with a milestone execution line and nested details.
- [x] Assemble consecutive model stream chunks into visible model output
      segments instead of one card per chunk.
- [x] Collapse completed run groups by default and expand into event details on
      demand.
- [x] Run backend unit/contract gates that do not require privileged MySQL DDL.
- [x] Run frontend unit, `remScaleClosure`, and production build.
- [x] Run browser UAT with real OpenRouter `qwen/qwen3.5-27b`.
- [x] Close MySQL8 integration/contract/e2e gates with the test admin URL.
- [x] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.

## 193.4 Product-Grade Event Echo And Same-Conversation Run History

- [x] RED: frontend timeline contract fails until tool start/output/completed
      events are aggregated into one invocation with `调用详情`/`输入`/`输出`.
- [x] RED: frontend timeline contract fails until duplicate thought summaries
      are removed both before and after matching model stream output.
- [x] RED: frontend shell contract fails until the left run-record navigation
      and global echo toggle are removed.
- [x] Render persisted historical runs as folded task records in the same
      conversation window.
- [x] Show only running nodes with a spinner; completed nodes use gray dots and
      completed headers use a green check indicator.
- [x] Remove generic `里程碑`/`动态事件` detail rows from event cards.
- [x] Add explicit usage units: `输入 tokens`, `输出 tokens`, `总计 tokens`,
      `耗时 ms`.
- [x] Run full frontend unit, `remScaleClosure`, production build, backend AI
      Assistant unit, and live Qwen/stream contract subset.
- [x] Run browser UAT with real OpenRouter `qwen/qwen3.5-27b`, including
      read tools, write approval, write execution, persisted replay, and
      screenshot evidence.
- [x] Close MySQL8 integration/contract/e2e gates with the test admin URL,
      keeping the implementation on MySQL8.
- [x] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.

## 193.5 Final Browser UAT And Completion Audit

- [x] Run a real browser UAT journey against `/ai-assistant` with OpenRouter
      `qwen/qwen3.5-27b`, temporary model config, model stream, read tool,
      skill intent, write approval, and write completion.
- [x] Verify the ReAct event order over time instead of a fixed mock list:
      running spinner before model output, model output before tool rows,
      tool rows before approval, and completed run after approval.
- [x] Verify one-screen layout, no old echo copy, usage units, task panel real
      content, and expanded tool details with `调用详情` / `输入` / `输出`.
- [x] Save browser UAT screenshots and JSON evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.5/`.

## 193.10 Blocker Recovery And Real Qwen Revalidation

- [x] RED: prove OpenRouter reasoning-only responses were being dropped or
      duplicated into visible model output.
- [x] RED: prove OpenRouter SSE `delta.reasoning` was not preserved by the
      OpenAI-compatible stream client.
- [x] Fix live planner text separation: `reasoning` becomes thought summary,
      while `content` remains the only visible model output stream.
- [x] Fix OpenRouter stream assembly to preserve reasoning outside visible
      `content` deltas.
- [x] Fix the model-config panel so it closes on send and cannot block approval
      actions.
- [x] Hide approval action buttons once the matching approval is no longer
      pending.
- [x] Resolve MySQL8 gate blocker by running tests with
      `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` against the local MySQL8 container,
      without introducing SQLite or PostgreSQL fallback.
- [x] Revalidate real OpenRouter `qwen/qwen3.5-27b` browser UAT with tool
      calling, write approval, approval execution, stream output, usage metrics,
      one-screen layout, and cleanup.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.10-blocker-recovery/`.

## 193.11 Complex Progress UAT And In-App Browser Bridge Check

- [x] RED: prove the right-side task row could enter `RUNNING` without a visible
      animation during complex live execution.
- [x] RED: prove the right-side execution-step list could miss a running spinner
      while qwen live planning was still active.
- [x] Add a complex browser UAT script covering real qwen3.5-27b streaming,
      workspace file read, knowledge-base search, skill intent, write approval,
      approval execution, final answer, and one-screen layout.
- [x] Fix the task/progress UI so only the active run's current planning step
      spins; historical completed steps resolve back to done icons.
- [x] Add stable approval button test ids and wait for the real approve API
      response in UAT.
- [x] Revalidate with frontend unit, remScaleClosure, full frontend unit, build,
      AI Assistant backend unit/contract with MySQL8 admin DSN, and real qwen
      browser UAT.
- [x] Record remaining risk: Codex in-app browser bridge still times out while
      attaching a webview; Playwright Chromium UAT against the same URL is green.

## 193.12 Current-Run Execution Steps And In-App Browser UAT Recovery

- [x] RED: frontend shell contract fails until right-panel execution steps use
      `inspectorExecutionStepsForView` instead of accumulated low-level model
      timeline events.
- [x] Scope execution steps to the currently selected/currently running run so
      each new user question starts with a clean step list.
- [x] Build execution steps from current-run model-planned tool names plus real
      tool call and approval records; hide low-level ReAct event names such as
      `思考摘要`, `工具调用决策`, `模型输出`, `文件操作意图`, and `技能调用意图`.
- [x] Fix execution-step state icons: running uses a dedicated spinner, completed
      uses a transparent green check icon, failed/denied uses the error icon, and
      waiting remains neutral.
- [x] Recover the Codex in-app browser bridge, run a real qwen3.5-27b complex
      journey in the in-app browser, approve the write action, and verify current
      run steps, icon states, running animation, final answer, and one-screen
      layout.
- [x] Extend the complex browser e2e script to assert current-question execution
      step scope and absence of low-level event labels.
- [x] Revalidate with focused frontend unit, remScaleClosure, full frontend unit,
      frontend build, AI Assistant backend unit/contract with MySQL8 admin DSN,
      scripted real qwen e2e, and in-app browser UAT evidence.

## 193.13 Codex-Like Output Grouping And Status Icons

- [x] RED: backend planner contract fails until repeated OpenRouter
      reasoning/content fragments are normalized before thought/model display.
- [x] RED: frontend timeline contract fails until duplicate adjacent model stream
      chunks are assembled into one clean assistant output segment.
- [x] RED: shell contract fails until user messages, peer-level assistant text,
      processed thought/tool groups, completion card actions, and dedicated
      task/execution status icons are exposed.
- [x] Fold processed thought/tool groups when model text appears, while keeping
      the visible assistant output at the same timeline level.
- [x] Render user message bubbles with subtle fill and no border; render pure
      assistant text without card background or border.
- [x] Add completion summary card controls for copy, like, and dislike.
- [x] Revalidate with backend planner unit, focused frontend unit, full frontend
      unit, remScaleClosure, frontend build, real qwen smoke, backend AI
      Assistant gate, and browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.13-codex-like-output-uat/`.

## 193.14 Duration MS Truthfulness

- [x] RED: duration unit contract fails because a real sub-millisecond tool
      execution is displayed as `0 ms`.
- [x] Preserve real backend `perf_counter` duration measurement while rounding
      nonzero elapsed milliseconds up to at least `1 ms`.
- [x] Apply the same duration helper to direct tool intent and dispatched tool
      execution paths.
- [x] Revalidate with duration unit, full AI Assistant unit, AI Assistant
      unit/integration/contract/e2e backend gate against MySQL8, and real
      in-app browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.14-duration-ms-truthfulness/`.

## 193.15 Agent Echo Polish And Orchestration Hardness

- [x] RED: frontend shell contract fails until completion summaries become plain
      assistant text, user messages show hover copy/time controls, compact
      chevrons sit after task/event title text, and event `#` sequence markers
      are removed.
- [x] RED: frontend timeline contract fails until visible event echo items are
      limited to `思考过程`, `工具调用`, `命令执行`, and `审批通过`, with tool cards
      showing result/content instead of raw JSON or start/completed noise.
- [x] RED: backend hardness tests fail until colloquial qwen plans supplement
      missed knowledge, skill, write, and readback tool calls while preserving
      staged read-only ReAct rounds and OpenAI tool-call ids.
- [x] RED: approval contract fails until approving a scheduled write continues
      pending readback tool calls before completing the run.
- [x] Polish the processed-run and nested event headers into one-line Chinese
      layout: status icon, title, compact meta, weak chevron, no sequence marker.
- [x] Align parent processed-run status icon and nested event status icons on the
      same execution rail center line.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, full frontend
      unit, frontend build, AI Assistant backend unit/integration/contract/e2e,
      real OpenRouter qwen3.5-27b smoke, and complex browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.15-agent-echo-polish-uat/`.

## 193.16 Tool Echo Summary Aggregation

- [x] RED: frontend timeline contract fails while one ReAct run with multiple
      low-level `tool.call_*` events renders repeated `工具调用` nodes instead of
      one foldable summary event.
- [x] RED: frontend timeline contract fails while running tool calls with no
      output produce no visible summarized running node.
- [x] RED: frontend timeline contract fails while completion-only `toolCallId`
      events create duplicate waiting-result details.
- [x] RED: frontend timeline contract fails while completed empty outputs such
      as `NOT_FOUND` render `等待结果` instead of a real status summary.
- [x] Aggregate all tool calls in a processed run into one visible `工具调用` or
      `命令执行` event while preserving readable per-tool input/output details.
- [x] Revalidate with focused frontend unit, AI Assistant shell unit,
      `remScaleClosure`, full frontend unit, frontend build, full AI Assistant
      backend unit/integration/contract/e2e, and in-app browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.16-tool-echo-summary-aggregation/`.

## 193.17 File Echo Separation And Tool Summary UI

- [x] RED: frontend timeline contract fails while grouped tool output still
      exposes multiple internal tool invocation cards instead of one product
      summary.
- [x] RED: frontend timeline contract fails until file read/write/create
      events become Codex-like top-level file echo nodes instead of generic
      `工具调用` nodes.
- [x] Split `read_workspace_file`, `write_workspace_file`, and
      `create_workspace_file` into `file` timeline buckets with Chinese
      `已读取/已编辑/已创建 N 个文件` headers and structured path/result details.
- [x] Keep non-file tools as a single summarized `工具调用`/`命令执行` invocation
      with formatted Chinese input/output rows, including `invoke_skill` as
      `使用技能` and no visible `skill=tdd` raw string.
- [x] Update processed-run meta and status icon handling so file operations are
      counted separately from tool calls in the folded task header.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, full frontend
      unit, frontend build, full AI Assistant backend unit/integration/contract/e2e,
      real OpenRouter qwen3.5-27b browser UAT, and `git diff --check`.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.17-file-echo-and-tool-summary-ui/`.

## 193.18 File Echo Polish Follow-Up

- [x] RED: frontend timeline contract fails while file details repeat both the
      operation label and `路径` for the same file.
- [x] RED: frontend shell contract fails until the folded `已处理` header stops
      counting file operations.
- [x] RED: frontend timeline contract fails until a multi-tool child header
      shows concrete tool names instead of another generic `工具调用`.
- [x] Remove duplicated `读取/编辑/创建：path` prefixes from file detail values
      and dedupe identical repeated file detail blocks for repeated readback.
- [x] Rename multi-tool invocation headers to a compact joined tool-name label
      such as `知识库检索、使用技能`.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, full frontend
      unit, frontend build, browser UAT, and `git diff --check`.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.18-file-echo-polish/`.

## 193.19 Icon Button And Chevron Polish

- [x] RED: frontend shell contract fails until icon-only buttons share one
      compact size contract and collapse arrows use SVG icon components instead
      of direction-character fallbacks.
- [x] Replace timeline fold arrows with `CollapseChevron` SVG icons and mark
      them `aria-hidden`.
- [x] Add AI Assistant scoped icon button size variables and apply them to
      session delete, message action, composer action, model config, and send
      icon-only buttons.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, full frontend
      unit, frontend build, `git diff --check`, and in-app browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.19-icon-button-polish/`.

## 193.20 Code Save And Test Attempt Pressure UAT

- [x] RED: frontend UAT script contract fails while
      `ai-assistant-code-save-test-uat.mjs` is missing.
- [x] Add a repeatable pressure UAT script that drives AI Assistant through
      code generation, workspace file write approval, readback verification,
      local execution of the saved code, and a shell test-run attempt.
- [x] Verify current Phase 1 sandbox behavior: `run_shell` is denied with
      `sandbox.denied` and the UI shows a visible `沙箱拒绝` error.
- [x] Revalidate persisted replay in the in-app browser: expanded run shows
      `已编辑 1 个文件` and `已读取 1 个文件`, while the right panel records
      the shell sandbox denial.
- [x] Revalidate with focused script contract, full frontend unit,
      frontend build, deterministic tool-stress UAT, in-app browser UAT, and
      `git diff --check`.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.20-code-save-test-uat/`.

## 193.21 Controlled Shell Approval And Echo Header Alignment

- [x] RED: sandbox boundary test fails while `run_shell` still blocks every
      command, including controlled `node tmp/...` workspace test commands.
- [x] RED: tool registry test fails while `run_shell` remains a blocked
      placeholder instead of returning stdout/stderr/exitCode.
- [x] RED: API contract fails while a successful controlled shell run does not
      surface stdout in the final answer.
- [x] RED: frontend shell contract fails while the folded `已处理` task echo
      header lacks explicit left-aligned grid/font constraints.
- [x] Allow only sandbox-approved controlled command execution under
      `always_approve`, keeping shell operators, non-allowlisted executables,
      node eval/print flags, and non-workspace script paths denied.
- [x] Execute allowed commands with `shell=False`, workspace cwd, timeout, and
      bounded stdout/stderr capture.
- [x] Update pressure UAT to switch to `完全访问权限`, save/read code, run the
      saved node test through AI Assistant, and verify stdout in command detail
      plus final answer.
- [x] Restore folded `已处理` header text to left-aligned compact row layout.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, frontend build,
      AI Assistant Python unit/contract gates, deterministic pressure UAT, and
      in-app browser UAT measurement.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.21-controlled-shell-approval/`.

## 193.22 Command Echo Shell Result UI

- [x] RED: frontend timeline contract fails while shell tool echoes still
      render the outer header as generic `命令执行` instead of
      `已运行 N 条命令`.
- [x] RED: frontend shell contract fails while command invocations lack a
      copyable Codex-like `Shell` result block.
- [x] Refactor `run_shell` timeline invocations into `displayMode: "shell"`
      with the real command as the fold header, no nested `终端命令` or
      `调用工具` rows, and Shell copy text assembled from command plus stdout.
- [x] Render expanded shell invocations as a single terminal-style result
      block with command, stdout/stderr, completion indicator, and a hover/focus
      copy button.
- [x] Keep shell command fold headers free of an inner completed icon and avoid
      duplicated completion text; the parent event line carries the completion
      status.
- [x] Update pressure UAT assertions to verify command headers, Shell result
      output, absence of old tool detail rows, and copy button presence.
- [x] Revalidate with focused frontend unit, `remScaleClosure`, full frontend
      unit, frontend build, deterministic pressure UAT, and in-app browser UAT.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.22-command-echo-shell-result-ui/`.

## 193.23 Shell Result Alignment Polish

- [x] RED: frontend shell contract fails while expanded Shell result blocks keep
      a third-level left indent under their command fold header.
- [x] Remove the Shell result block left margin so the expanded command output
      aligns with its foldable command header.
- [x] Extend the pressure UAT script with a browser geometry assertion that
      `shellResultLeftDelta` stays within `1px`.
- [x] Revalidate with focused frontend unit, AI Assistant timeline/shell unit,
      `remScaleClosure`, full frontend unit, frontend build, deterministic
      pressure UAT, and Codex in-app browser UAT using OpenRouter
      `qwen/qwen3.5-27b`.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.23-shell-result-alignment/`.
