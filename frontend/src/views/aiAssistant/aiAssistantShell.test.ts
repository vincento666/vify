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
      'ai-assistant-event-stream',
      'ai-assistant-event-card',
      'ai-assistant-event-card-header',
      'ai-assistant-composer',
      'ai-assistant-send',
      'ai-assistant-session-list',
      'ai-assistant-session-row',
      'ai-assistant-run-row',
      'ai-assistant-clear-history',
      'ai-assistant-delete-session',
      'ai-assistant-stream-toggle',
      'ai-assistant-run-inspector',
      'ai-assistant-task-row',
      'ai-assistant-tool-call-row',
      'ai-assistant-approval-row',
      'ai-assistant-recent-error-row',
      'ai-assistant-inspector-timeline',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
    expect(content).toContain('buildAiAssistantTimeline')
    expect(content).toContain('loadRunInspector')
    expect(content).toContain('statusPulse')
    expect(content).toContain('streamPulse')
    expect(content).not.toContain('chain-of-thought')
  })

  it('exposes stable controls for browser UAT and avoids mock-looking session titles', () => {
    expect(content).toContain('aria-label="新建 AI 助手会话"')
    expect(content).toContain(':aria-pressed="run.id === runId"')
    expect(content).toContain('createAiAssistantSession()')
    expect(content).toContain('会话 #')
    expect(content).toContain('sessionDisplayTitle(session)')
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
    expect(content).toContain('grid-template-rows: auto minmax(0, 1fr)')
    expect(content).toContain('data-testid="ai-assistant-left-column-scroll"')
    expect(content).toContain('ai-assistant-center-column-scroll')
    expect(content).toContain('ai-assistant-right-column-scroll')
    expect(content).not.toContain('height: auto;')
  })

  it('uses only the outer shell border instead of inline module borders', () => {
    const solidBorders = content.match(/border: 0\.0625rem solid/g) ?? []
    expect(content).toContain('.ai-shell {')
    expect(content).toContain('border: 0.0625rem solid var(--color-border-default, #e3e6ef);')
    expect(content).toContain('.ai-shell :deep(.ant-btn),')
    expect(content).toContain('.ai-shell :deep(.ant-input),')
    expect(content).toContain('.ai-shell :deep(.ant-tag)')
    expect(solidBorders).toHaveLength(1)
    expect(content).not.toContain('border-top: 0.0625rem solid')
    expect(content).not.toContain('border-bottom: 0.0625rem solid')
  })

  it('defaults execution echo cards to collapsed details with header toggles', () => {
    expect(content).toContain('expandedEventIds')
    expect(content).toContain('toggleEventCard')
    expect(content).toContain('isEventExpanded')
    expect(content).toContain(':aria-expanded="isEventExpanded(item.id)"')
    expect(content).toContain('v-if="isEventExpanded(item.id)"')
    expect(content).toContain('eventStreamCollapsed')
    expect(content).toContain('回显')
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

  it('uses Chinese visible copy for the whole AI Assistant feature', () => {
    for (const label of [
      'Hify AI 助手',
      '新建会话',
      '运行记录',
      '执行中',
      '空闲',
      '输入给 AI 助手的消息',
      '任务',
      '工具调用',
      '审批',
      '最近错误',
      '用量',
      '时间线',
      '批准',
      '拒绝',
      '清空历史上下文',
      '删除会话',
      '展开',
      '收起',
      'Qwen3.5-27B',
      '读取工作区文件',
      '写入工作区文件',
      '技能意图',
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
    ]) {
      expect(content).not.toContain(englishCopy)
    }
  })
})
