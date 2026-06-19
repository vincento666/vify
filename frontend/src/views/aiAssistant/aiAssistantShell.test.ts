// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

describe('AI Assistant shell UI contract', () => {
  const content = readProjectFile('src/views/aiAssistant/AiAssistantShell.vue')

  it('renders conversation timeline composer and execution echo regions', () => {
    for (const testId of [
      'ai-assistant-shell',
      'ai-assistant-new-session',
      'ai-assistant-conversation-window',
      'ai-assistant-runtime-config',
      'ai-assistant-model-select',
      'ai-assistant-model-config-panel',
      'ai-assistant-model-config-icon',
      'ai-assistant-event-stream',
      'ai-assistant-event-card',
      'ai-assistant-event-card-header',
      'ai-assistant-assistant-message',
      'ai-assistant-composer',
      'ai-assistant-composer-body',
      'ai-assistant-composer-actions',
      'ai-assistant-add-context',
      'ai-assistant-permission-mode',
      'ai-assistant-send',
      'ai-assistant-session-list',
      'ai-assistant-session-row',
      'ai-assistant-clear-history',
      'ai-assistant-delete-session',
      'ai-assistant-run-inspector',
      'ai-assistant-task-row',
      'ai-assistant-tool-call-row',
      'ai-assistant-approval-row',
      'ai-assistant-recent-error-row',
      'ai-assistant-inspector-timeline',
      'ai-assistant-run-task-card',
      'ai-assistant-message-copy',
      'ai-assistant-user-message-meta',
      'ai-assistant-completion-meta',
      'ai-assistant-run-status-icon',
      'ai-assistant-event-status-icon',
      'ai-assistant-event-completed-icon',
      'ai-assistant-node-spinner',
      'ai-assistant-run-final-answer',
      'ai-assistant-task-status-icon',
      'ai-assistant-task-spinner',
      'ai-assistant-task-completed-icon',
      'ai-assistant-execution-step-spinner',
      'ai-assistant-execution-step-done',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
    expect(content).toContain('buildAiAssistantTimeline')
    expect(content).toContain('loadRunThreadRecords')
    expect(content).toContain('runThreads')
    expect(content).toContain('isEventRunning')
    expect(content).toContain('实时事件流')
    expect(content).toContain('qwen/qwen3.5-27b')
    expect(content).toContain('https://openrouter.ai/api/v1')
    expect(content).toContain('临时密钥')
    expect(content).not.toContain('chain-of-thought')
    expect(content).not.toContain('data-testid="ai-assistant-run-row"')
    expect(content).not.toContain('data-testid="ai-assistant-stream-toggle"')
  })

  it('exposes stable controls for browser UAT and avoids mock-looking session titles', () => {
    expect(content).toContain('aria-label="新建 AI 助手会话"')
    expect(content).toContain('createAiAssistantSession()')
    expect(content).toContain('会话 #')
    expect(content).toContain('sessionDisplayTitle(session)')
    expect(content).toContain('Qwen / qwen3.5-27B')
    expect(content).not.toContain("createAiAssistantSession({ title: 'Hify AI 助手' })")
    expect(content).not.toContain('sessionDisplayTitle(session.title)')
  })

  it('separates pending approvals from approval history in the inspector', () => {
    expect(content).toContain('pendingApprovals')
    expect(content).toContain('approvalRecords')
    expect(content).toContain('decidedApprovalRecords')
    expect(content).toContain('v-for="approval in pendingApprovals"')
    expect(content).toContain('data-testid="ai-assistant-approval-history-row"')
    expect(content).not.toContain('v-for="approval in inspector?.approvalQueue || []"')
  })

  it('keeps the assistant workbench one screen tall with internal column scrolling', () => {
    expect(content).toContain('height: calc(100vh - var(--header-height, 3.5rem) - 3rem)')
    expect(content).toContain('box-sizing: border-box')
    expect(content).toContain('overflow: hidden')
    expect(content).toContain('grid-template-rows: auto minmax(0, 1fr) auto')
    expect(content).toContain('scrollbar-gutter: stable;')
    expect(content).toContain('overflow-y: auto;')
    expect(content).toContain('overflow-x: hidden;')
    expect(content).toContain('padding: 0.625rem 0.375rem 0.625rem 0.625rem;')
    expect(content).toContain('data-testid="ai-assistant-left-column-scroll"')
    expect(content).toContain('ai-assistant-center-column-scroll')
    expect(content).toContain('ai-assistant-right-column-scroll')
    expect(content).not.toContain('height: auto;')
  })

  it('removes the extra shell padding and compresses the main AI Assistant content margins', () => {
    expect(content).toContain('gap: 0;')
    expect(content).toContain('padding: 0;')
    expect(content).toContain('padding: 0.625rem;')
    expect(content).toContain('padding: 0.625rem 0.625rem;')
    expect(content).toContain('padding: 0.625rem;')
    expect(content).not.toContain('gap: 1rem;')
    expect(content).not.toContain('padding: 1rem;')
    expect(content).not.toContain('padding: 0.875rem 1rem;')
  })

  it('uses only the outer shell border instead of inline module borders', () => {
    const solidBorders = content.match(/border: 0\.0625rem solid/g) ?? []
    expect(content).toContain('.ai-shell {')
    expect(content).toContain('border: 0.0625rem solid var(--color-border-default, #e3e6ef);')
    expect(content).toContain('.ai-shell :deep(.ant-btn),')
    expect(content).toContain('.ai-shell :deep(.ant-input),')
    expect(content).toContain('.ai-shell :deep(.ant-select-selector),')
    expect(content).toContain('.ai-shell :deep(.ant-tag)')
    expect(solidBorders).toHaveLength(1)
    expect(content).not.toContain('border-top: 0.0625rem solid')
    expect(content).not.toContain('border-bottom: 0.0625rem solid')
  })

  it('submits live messages without frontend tool heuristics', () => {
    expect(content).toContain('startAiAssistantMessage')
    expect(content).toContain('openAiAssistantEventStream')
    expect(content).toContain('buildAiAssistantMessagePayload(message, runtimeConfig.value')
    expect(content).toContain('runtimeConfig.value')
    expect(content).toContain('qwen/qwen3.5-27b')
    expect(content).toContain('https://openrouter.ai/api/v1')
    expect(content).not.toContain('asksForUpdate')
    expect(content).not.toContain("toolName: asksForUpdate ? 'update_customer_profile' : 'echo_context'")
    expect(content).not.toContain("toolInput: asksForUpdate ? { customerId: 'ui-customer', request: message } : undefined")
  })

  it('defaults execution echo cards to collapsed details with header toggles', () => {
    expect(content).toContain('expandedEventIds')
    expect(content).toContain('toggleEventCard')
    expect(content).toContain('isEventExpanded')
    expect(content).toContain(':aria-expanded="isEventExpanded(eventItem.id)"')
    expect(content).toContain('v-if="isEventExpanded(eventItem.id)"')
    expect(content).toContain("eventItem.kind === 'model-thought'")
    expect(content).toContain('ai-assistant-thought-summary')
    expect(content).toContain('isEventRunning')
    expect(content).toContain('LoadingOutlined')
    expect(content).toContain('data-testid="ai-assistant-assistant-message"')
    expect(content).not.toContain('eventStreamCollapsed')
    expect(content).not.toContain('收起回显')
    expect(content).not.toContain('展开回显')
  })

  it('groups live execution echoes into a collapsible run task with a milestone line and nested details', () => {
    for (const testId of [
      'ai-assistant-run-event-group',
      'ai-assistant-run-event-group-header',
      'ai-assistant-run-task-card',
      'ai-assistant-run-event-line',
      'ai-assistant-event-status-icon',
      'ai-assistant-event-completed-icon',
      'ai-assistant-event-detail-panel',
      'ai-assistant-event-detail-row',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
    expect(content).toContain('processedGroupExpanded')
    expect(content).toContain('toggleProcessedGroup')
    expect(content).toContain('isProcessedGroupExpanded')
    expect(content).toContain('formatEventDetailRows')
    expect(content).toContain('eventStatusIcon')
    expect(content).toContain('ai-collapse-chevron')
    expect(content).toContain('animation: ai-spin')
    expect(content).not.toContain('ai-event__pulse')
    expect(content).not.toContain('已收纳')
    expect(content).not.toContain('任务记录 #')
    expect(content).not.toContain('里程碑')
    expect(content).not.toContain('动态事件')
    expect(content).not.toContain('运行记录')
  })

  it('keeps run card headers compact and renders final answers outside folded echo cards', () => {
    expect(content).toContain('runThreadUserMessage(thread)')
    expect(content).toContain('data-testid="ai-assistant-user-message"')
    expect(content).toContain('runThreadPresentationItems(thread)')
    expect(content).toContain('runThreadFinalAnswer(thread)')
    expect(content).toContain('data-testid="ai-assistant-run-final-answer"')
    expect(content).toContain('data-testid="ai-assistant-completion-copy"')
    expect(content).toContain('data-testid="ai-assistant-completion-like"')
    expect(content).toContain('data-testid="ai-assistant-completion-dislike"')
    expect(content).toContain('已处理')
    expect(content).not.toContain('runThreadHeaderTitle(thread)')
    expect(content).not.toContain('function runThreadHeaderTitle')
    expect(content).not.toContain('<small>任务记录 #{{ thread.run.id }}</small>')
    expect(content).not.toContain('runTitle(thread.run)')
    expect(content).not.toContain('function runTitle')
    expect(content).not.toContain('statusLabel(thread.inspector?.run.status ?? thread.run.status)} / ${timeline.length} 条事件')
  })

  it('renders processed groups and model text as peer-level Codex-like timeline items', () => {
    expect(content).toContain('data-testid="ai-assistant-processed-group"')
    expect(content).toContain('data-testid="ai-assistant-assistant-message"')
    expect(content).toContain('processedGroupMeta(item.items)')
    expect(content).toContain('presentationItemKey(item)')
    expect(content).toContain('buildRunThreadPresentationItems')
    expect(content).toContain("item.kind === 'processed'")
    expect(content).toContain("item.kind === 'assistant-output'")
    expect(content).toContain('思考')
    expect(content).not.toContain('文件操作')
    expect(content).toContain('工具调用')
    expect(content).toContain("kind === 'file'")
    expect(content).toContain('EditOutlined')
  })

  it('renders nested formatted tool invocations inside one summarized tool event', () => {
    expect(content).toContain('eventItem.toolInvocations')
    expect(content).toContain('data-testid="ai-assistant-tool-invocation-list"')
    expect(content).toContain('data-testid="ai-assistant-tool-invocation"')
    expect(content).toContain('data-testid="ai-assistant-tool-invocation-header"')
    expect(content).toContain('data-testid="ai-assistant-tool-invocation-details"')
    expect(content).toContain('toggleToolInvocation')
    expect(content).toContain('isToolInvocationExpanded')
    expect(content).toContain('toolInvocationRows')
    expect(content).toContain('使用技能')
    expect(content).not.toContain('技能意图')
    expect(content).not.toContain('skill={{')
    expect(content).not.toContain('skill=')
  })

  it('renders command invocations as copyable Codex-like shell result blocks', () => {
    expect(content).toContain("toolInvocation.displayMode === 'shell'")
    expect(content).toContain("'ai-tool-invocation__header--shell': toolInvocation.displayMode === 'shell'")
    expect(content).toContain('v-if="toolInvocation.displayMode !== \'shell\'"')
    expect(content).toContain('v-if="toolInvocation.subtitle"')
    expect(content).toContain('data-testid="ai-assistant-shell-result"')
    expect(content).toContain('data-testid="ai-assistant-shell-result-output"')
    expect(content).toContain('data-testid="ai-assistant-shell-result-copy"')
    expect(content).toContain('copyToolInvocationResult')
    expect(content).toContain('toolInvocationShellOutput(toolInvocation)')
    expect(content).toContain('.ai-shell-result:hover .ai-shell-result__copy')
    expect(content).toContain('.ai-shell-result:focus-within .ai-shell-result__copy')
    expect(content).toContain('Shell')
  })

  it('left aligns expanded shell result blocks with their command fold header', () => {
    expect(content).toContain('.ai-shell-result {')
    expect(content).toContain('margin-left: 0;')
    expect(content).not.toContain('.ai-shell-result {\n  position: relative;\n  display: grid;\n  gap: 0.625rem;\n  margin-left: 1.5rem;')
  })

  it('renders user bubbles with subtle fill and completion summary cards with actions', () => {
    expect(content).toContain('class="ai-message ai-message--user"')
    expect(content).toContain('class="ai-message ai-message--assistant"')
    expect(content).toContain('class="ai-message ai-message--assistant ai-message--completion"')
    expect(content).toContain('.ai-message {')
    expect(content).toContain('.ai-message--user p {')
    expect(content).toContain('background: var(--color-bg-selected, #eef2ff);')
    expect(content).toContain('border: 0;')
    expect(content).toContain('data-testid="ai-assistant-message-copy"')
    expect(content).toContain('data-testid="ai-assistant-user-message-meta"')
    expect(content).toContain('data-testid="ai-assistant-completion-meta"')
    expect(content).toContain('.ai-message__actions')
    expect(content).toContain('.ai-message:hover .ai-message__actions')
    expect(content).toContain('opacity: 0;')
    expect(content).not.toContain('class="ai-completion-card"')
    expect(content).not.toContain('<strong>任务完成</strong>')
    expect(content).not.toContain('>复制<')
    expect(content).not.toContain('>点赞<')
    expect(content).not.toContain('>点踩<')
  })

  it('uses compact right-side chevrons after title text for task and event folding', () => {
    expect(content).toContain('CollapseChevron')
    expect(content).toContain('class="ai-collapse-chevron"')
    expect(content).toContain('class="ai-run-event-group__title-text"')
    expect(content).toContain('class="ai-run-event-group__meta"')
    expect(content).toContain('class="ai-event__title-text"')
    expect(content).toContain(':class="{ expanded: isProcessedGroupExpanded(item, thread) }"')
    expect(content).toContain(':class="{ expanded: isEventExpanded(eventItem.id) }"')
    expect(content).toContain('grid-template-columns: auto auto auto auto;')
    expect(content).toContain('grid-template-columns: auto auto minmax(0, 1fr);')
    expect(content).toContain('white-space: nowrap;')
    expect(content).toContain('padding-left: 0.75rem;')
    expect(content).toContain('color: var(--color-text-tertiary, #8b92a8);')
    expect(content).not.toContain('<small>{{ processedGroupMeta(item.items) }}</small>')
    expect(content).not.toContain('class="ai-event__meta"')
    expect(content).not.toContain('#{{ eventItem.sequence }}')
    expect(content).not.toContain('<DownOutlined v-if="!isProcessedGroupExpanded(item, thread)" />')
    expect(content).not.toContain('<UpOutlined v-else />')
    expect(content).not.toContain('<DownOutlined v-if="!isEventExpanded(eventItem.id)" />')
    expect(content).not.toContain('<UpOutlined v-else />')
  })

  it('keeps processed run echo headers left aligned without stretched grid text', () => {
    expect(content).toContain('.ai-run-event-group__header {')
    expect(content).toContain('justify-content: start;')
    expect(content).toContain('justify-items: start;')
    expect(content).toContain('text-align: left;')
    expect(content).toContain('.ai-run-event-group__title-text {')
    expect(content).toContain('font-size: 0.9375rem;')
    expect(content).toContain('line-height: 1.25;')
    expect(content).toContain('.ai-run-event-group__meta {')
    expect(content).toContain('line-height: 1.25;')
  })

  it('uses compact unified icon buttons and svg-only collapse arrows', () => {
    expect(content).toContain('RightOutlined as CollapseChevron')
    expect(content).toContain('<CollapseChevron')
    expect(content).toContain('aria-hidden="true"')
    expect(content).toContain('--ai-icon-button-size: 1.875rem;')
    expect(content).toContain('--ai-icon-glyph-size: 0.875rem;')
    expect(content).toContain('.ai-shell :deep(.ant-btn-icon-only)')
    expect(content).toContain('.ai-shell :deep(.ant-btn .anticon)')
    expect(content).not.toContain('CaretRightOutlined as CollapseChevron')
    expect(content).not.toContain('RightOutlined as ChevronRight')
    expect(content).not.toContain('<ChevronRight')
    expect(content).not.toContain('>›<')
    expect(content).not.toContain('>><')
  })

  it('groups inspector stream chunks and hides stale approval actions', () => {
    expect(content).toContain('inspectorExecutionStepsForView')
    expect(content).toContain('currentRunEventsForView')
    expect(content).toContain('buildInspectorExecutionSteps')
    expect(content).toContain('plannedToolNamesFromCurrentRun')
    expect(content).toContain('normalizeCurrentRunExecutionSteps')
    expect(content).toContain('执行步骤')
    expect(content).toContain('ai-execution-steps')
    expect(content).toContain('data-testid="ai-assistant-execution-step"')
    expect(content).toContain('v-for="step in inspectorExecutionStepsForView"')
    expect(content).toContain('isCurrentInspectorStep(step)')
    expect(content).toContain("inspector.value?.run.status === 'RUNNING'")
    expect(content).toContain('taskMetaLabel(task)')
    expect(content).toContain('shouldShowApprovalActions(eventItem, thread)')
    expect(content).toContain('approvalStatusForTimelineItem')
    expect(content).toContain('isPendingApprovalStatus(approval.status)')
    expect(content).toContain('isDoneInspectorStepStatus(step.status)')
    expect(content).toContain('ai-execution-step__pending')
    expect(content).toContain('data-testid="ai-assistant-approval-approve"')
    expect(content).toContain('data-testid="ai-assistant-approval-deny"')
    expect(content).toContain('data-testid="ai-assistant-task-status-icon"')
    expect(content).toContain('data-testid="ai-assistant-task-spinner"')
    expect(content).toContain('data-testid="ai-assistant-task-completed-icon"')
    expect(content).not.toContain('class="ai-task__dot"')
    expect(content).not.toContain('.ai-task__dot.status-running')
    expect(content).not.toContain("return !isInspectorEventRunning(step) && step.status !== 'FAILED' && step.status !== 'DENIED'")
    expect(content).not.toContain('<header>时间线</header>')
    expect(content).not.toContain('v-for="event in inspector?.eventTimeline || []"')
    expect(content).not.toContain('v-for="event in inspectorPlanningStepsForView"')
    expect(content).not.toContain('isModelPlanningInspectorEvent')
    expect(content).not.toContain('model.thought_summary')
    expect(content).not.toContain('item.kind === \'approval\' && item.approvalId"')
  })

  it('keeps temporary model configuration across a browser reload without using long term storage', () => {
    expect(content).toContain('AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY')
    expect(content).toContain('sessionStorage')
    expect(content).toContain('watch(runtimeConfig')
    expect(content).not.toContain('localStorage')
  })

  it('places clear context in the conversation header and delete on each session row', () => {
    expect(content).toContain('data-testid="ai-assistant-clear-history"')
    expect(content).toContain('清空历史上下文')
    expect(content).toContain('class="ai-console__actions"')
    expect(content).toContain('data-testid="ai-assistant-delete-session"')
    expect(content).toContain('@click.stop="deleteConversation(session.id)"')
    expect(content).toContain('class="ai-session__delete"')
    expect(content).not.toContain('class="ai-session-actions"')
  })

  it('uses a Codex-like composer with permission mode and model settings controls', () => {
    expect(content).toContain('class="ai-composer__body"')
    expect(content).toContain('data-testid="ai-assistant-composer-body"')
    expect(content).toContain('class="ai-composer__actions"')
    expect(content).toContain('data-testid="ai-assistant-composer-actions"')
    expect(content).toContain('data-testid="ai-assistant-add-context"')
    expect(content).toContain('data-testid="ai-assistant-permission-mode"')
    expect(content).toContain('permissionModeLabel')
    expect(content).toContain('selectPermissionMode')
    expect(content).toContain('请求批准')
    expect(content).toContain('替我审批')
    expect(content).toContain('完全访问权限')
    expect(content).toContain('data-testid="ai-assistant-model-config-icon"')
    expect(content).toContain('data-testid="ai-assistant-model-config-panel"')
    expect(content).toContain('class="ai-composer__model-panel"')
    expect(content).not.toContain('class="ai-runtime__toggle"')
    expect(content).not.toContain('class="ai-runtime__summary"')
    expect(content).toContain("buildAiAssistantMessagePayload(message, runtimeConfig.value, `ui-${Date.now()}`, permissionMode.value)")
    expect(content).toContain('runtimeConfigExpanded.value = false')
  })

  it('uses Chinese visible copy for the whole AI Assistant feature', () => {
    for (const label of [
      'Hify AI 助手',
      '新建会话',
      '执行中',
      '空闲',
      '输入给 AI 助手的消息',
      '模型',
      '模型配置',
      '接口地址',
      '温度',
      '输出上限',
      '实时事件流：已启用',
      '任务',
      '工具调用',
      '审批',
      '最近错误',
      '用量',
      '输入 tokens',
      '输出 tokens',
      '总计 tokens',
      '耗时 ms',
      '执行步骤',
      '批准',
      '拒绝',
      '清空历史上下文',
      '删除会话',
      'Qwen / qwen3.5-27B',
      '临时密钥',
      '读取工作区文件',
      '写入工作区文件',
      '使用技能',
      '知识库检索',
      '可观测性',
    ]) {
      expect(content).toContain(label)
    }

    for (const englishCopy of [
      '>New Run<',
      '>Runs<',
      '>Tasks<',
      '>Tool Calls<',
      '>Approvals<',
      '>Recent Errors<',
      '>Usage<',
      '>Timeline<',
      'placeholder="Message AI Assistant"',
      '>Approve<',
      '>Deny<',
      '>Ready<',
      'SSE 预留',
      '临时 API Key',
      '>Base URL<',
      '>Temperature<',
      '>Max Tokens<',
    ]) {
      expect(content).not.toContain(englishCopy)
    }
  })
})
