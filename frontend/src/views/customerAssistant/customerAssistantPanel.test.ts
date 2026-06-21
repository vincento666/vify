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

function elementByTestId(content: string, testId: string) {
  const marker = `data-testid="${testId}"`
  const markerIndex = content.indexOf(marker)
  if (markerIndex < 0) return ''

  const tagStart = content.lastIndexOf('<', markerIndex)
  if (tagStart < 0) return ''

  const tagMatch = /^<([a-zA-Z][\w-]*)\b/.exec(content.slice(tagStart))
  if (!tagMatch) return ''

  const tag = tagMatch[1]
  const tagPattern = new RegExp(`<\\/?${tag}\\b[^>]*>`, 'g')
  tagPattern.lastIndex = tagStart

  let depth = 0
  for (let match = tagPattern.exec(content); match; match = tagPattern.exec(content)) {
    const token = match[0]
    if (token.startsWith('</')) {
      depth -= 1
    } else if (!token.endsWith('/>')) {
      depth += 1
    }

    if (depth === 0) {
      return content.slice(tagStart, tagPattern.lastIndex)
    }
  }

  return content.slice(tagStart)
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

function testIdIndex(content: string, testId: string) {
  return content.indexOf(`data-testid="${testId}"`)
}

describe('CustomerAssistantPanel IA convergence contract', () => {
  const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

  it('keeps the product shell in left center and right workbench columns', () => {
    expect(content).toContain('data-testid="customer-assistant-workspace"')
    expect(content).toContain('data-testid="customer-assistant-three-column-shell"')
    expect(content).toContain('data-testid="customer-assistant-left-column"')
    expect(content).toContain('data-testid="customer-assistant-center-column"')
    expect(content).toContain('data-testid="customer-assistant-ai-workbench-column"')
    expect(elementByTestId(content, 'customer-assistant-center-column')).not.toContain('operator-task-ledger')
    expect(elementByTestId(content, 'customer-assistant-center-column')).not.toContain('operator-worker-profile-config-panel')
  })

  it('contracts the right workbench to focus, assistant, evidence, and config tabs only', () => {
    const tabs = elementByTestId(content, 'operator-ai-workbench-tabs')

    expect(tabs).toContain('聚焦')
    expect(tabs).toContain('AI助手')
    expect(tabs).toContain('证据')
    expect(tabs).toContain('配置')
    expect(regexMatches(tabs, /role="tab"/g)).toHaveLength(4)
    expect(tabs).not.toContain('办理')
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'focus'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'assistant'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'evidence'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'config'\"")
    expect(content).not.toContain("activeWorkbenchTab === 'business'")
    expect(content).not.toContain('data-testid="operator-workbench-business-pane"')
  })

  it('makes focus the default business closure workspace around one production task intent flow', () => {
    const focusPane = elementByTestId(content, 'operator-workbench-focus-pane')

    for (const testId of [
      'operator-focus-status-bar',
      'operator-focus-sop-handling-tree',
      'operator-focus-intent-emotion-card',
      'operator-focus-business-object-summary',
      'operator-focus-risk-sla-card',
      'operator-focus-recommended-reply-card',
      'operator-focus-sensitive-confirmation-card',
    ]) {
      expect(focusPane).toContain(`data-testid="${testId}"`)
    }

    expect(testIdIndex(focusPane, 'operator-focus-status-bar')).toBeLessThan(
      testIdIndex(focusPane, 'operator-focus-sop-handling-tree'),
    )
    expect(testIdIndex(focusPane, 'operator-focus-sop-handling-tree')).toBeLessThan(
      testIdIndex(focusPane, 'operator-focus-intent-emotion-card'),
    )
    expect(regexMatches(focusPane, /data-testid="operator-focus-recommended-reply-card"/g)).toHaveLength(1)
    expect(regexMatches(focusPane, /data-testid="operator-focus-sensitive-confirmation-card"/g)).toHaveLength(1)
    const recommendedReplyCard = elementByTestId(focusPane, 'operator-focus-recommended-reply-card')
    const sensitiveConfirmationCard = elementByTestId(focusPane, 'operator-focus-sensitive-confirmation-card')

    expect(focusPane).toContain('状态条')
    expect(focusPane).toContain('任务意图分析')
    expect(focusPane).toContain('思考摘要')
    expect(focusPane).toContain('情绪')
    expect(focusPane).toContain('业务对象摘要')
    expect(focusPane).toContain('SOP办理树')
    expect(focusPane).toContain('风险与时效')
    expect(focusPane).toContain('推荐回复')
    expect(focusPane).toContain('高敏确认')
    expect(focusPane).toContain('workspace.proposedActions')
    expect(focusPane).toContain('workspace.taskSummary.items')
    expect(focusPane).toContain('data-testid="operator-focus-task-controls"')
    expect(recommendedReplyCard).toContain('workspace.recommendation.customerReplyDraft')
    expect(recommendedReplyCard).toContain('坐席处理提示')
    expect(recommendedReplyCard).toContain(':disabled="!hasDraft"')
    expect(recommendedReplyCard).not.toContain(':disabled="!workspace.recommendation.operatorRecommendation"')
    expect(sensitiveConfirmationCard).toContain('pendingProposedActions.length')
    expect(sensitiveConfirmationCard).toContain('查看依据与回执')
    expect(sensitiveConfirmationCard).toContain('data-testid="operator-action-receipt"')
    expect(sensitiveConfirmationCard).toContain('data-testid="operator-draft-delivery-receipt"')
    expect(sensitiveConfirmationCard).toContain('data-testid="operator-action-decision-receipt"')
    expect(focusPane).not.toContain('data-testid="operator-task-ledger"')
    expect(focusPane).not.toContain('data-testid="operator-recommendation-panel"')
    expect(focusPane).not.toContain('data-testid="operator-draft-panel"')
    expect(focusPane).not.toContain('data-testid="operator-proposed-actions-panel"')
    expect(focusPane).not.toContain('data-testid="operator-task-controls"')
    expect(focusPane).not.toContain('data-testid="operator-worker-profile-config-panel"')
    expect(focusPane).not.toContain('data-testid="operator-eval-observability-panel"')
    expect(focusPane).not.toContain('modelPolicyRef')
    expect(focusPane).not.toContain('promptRef')
    expect(focusPane).not.toContain('workerRunId')
    expect(focusPane).not.toContain('Worker 配置')
  })

  it('renders the assistant tab as a pure chat window without internal task or config panels', () => {
    const assistantPane = elementByTestId(content, 'operator-workbench-assistant-pane')
    const chatWindow = elementByTestId(content, 'operator-assistant-chat-window')

    expect(assistantPane).toContain('data-testid="operator-assistant-chat-window"')
    expect(chatWindow).toContain('class="assistant-chat-window"')
    expect(chatWindow).toContain('data-testid="operator-assistant-chat-messages"')
    expect(chatWindow).toContain('data-testid="operator-assistant-chat-composer"')
    expect(assistantPane).toContain('askOperatorKnowledgeQuestion')
    expect(chatWindow).not.toContain('data-testid="operator-assistant-chat-header"')
    expect(chatWindow).not.toContain('<header')
    expect(chatWindow).not.toContain('panel-heading')
    expect(chatWindow).not.toContain('data-testid="operator-knowledge-qa-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-task-ledger"')
    expect(assistantPane).not.toContain('data-testid="operator-task-controls"')
    expect(assistantPane).not.toContain('data-testid="operator-warnings-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-metrics-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-worker-profile-config-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-eval-observability-panel"')
    expect(assistantPane).not.toContain('workspace.proposedActions')
    expect(assistantPane).not.toContain('workspace.taskSummary')
    expect(assistantPane).not.toContain('workerProfiles')
    expect(assistantPane).not.toContain('profile.modelPolicyRef')
  })

  it('marks evidence and config as research debugging entries instead of normal handling tabs', () => {
    const evidencePane = elementByTestId(content, 'operator-workbench-evidence-pane')
    const configPane = elementByTestId(content, 'operator-workbench-config-pane')

    expect(evidencePane).toContain('研究调试入口')
    expect(configPane).toContain('研究调试入口')
    expect(evidencePane).toContain('data-testid="operator-eval-observability-panel"')
    expect(evidencePane).toContain('data-testid="operator-recognition-evidence-panel"')
    expect(evidencePane).toContain('data-testid="operator-advisory-evidence-panel"')
    expect(evidencePane).toContain('data-testid="operator-audit-panel"')
    expect(configPane).toContain('data-testid="operator-worker-profile-config-panel"')
    expect(configPane).toContain('workerProfiles')
    expect(configPane).toContain('profile.workerRef')
    expect(configPane).toContain('profile.modelPolicyRef')
    expect(configPane).toContain('profile.promptRef')
  })

  it('keeps the center operator lane passenger-facing and free of assistant tooling', () => {
    const centerColumn = elementByTestId(content, 'customer-assistant-center-column')
    const operatorLane = elementByTestId(content, 'operator-conversation-lane')

    expect(operatorLane).toContain('坐席发话')
    expect(operatorLane).toContain('旅客对话')
    expect(operatorLane).toContain('模拟坐席发话')
    expect(operatorLane).toContain('发送给旅客的话术')
    expect(operatorLane).not.toContain('追问助手')
    expect(operatorLane).not.toContain('Worker 配置')
    expect(operatorLane).not.toContain('operator-task-ledger')
    expect(centerColumn).not.toContain('operatorKnowledgeQuestion')
    expect(centerColumn).not.toContain('operator-worker-profile-config-panel')
  })

  it('keeps compact viewports as a three-column shell instead of collapsing into a vertical panel stack', () => {
    expect(content).toContain('grid-template-columns: repeat(4, minmax(0, 1fr));')
    expect(content).toMatch(/@media \(max-width: 58rem\)[\s\S]*\.customer-assistant-shell \{[\s\S]*grid-template-columns: minmax\(10\.5rem, 11rem\) minmax\(0, 1fr\) minmax\(10\.5rem, 11rem\);/)
    expect(content).not.toMatch(/@media \(max-width: 58rem\)[\s\S]*\.customer-assistant-shell,[\s\S]*display: flex/)
  })

  it('constrains the shell to one viewport and scrolls overflowing columns internally', () => {
    expect(content).toMatch(/\.customer-assistant-shell \{[\s\S]*height: calc\(100vh - 8rem\);[\s\S]*overflow: hidden;/)
    expect(content).toMatch(/\.customer-assistant-left-column,[\s\S]*\.customer-assistant-center-column,[\s\S]*\.customer-assistant-ai-workbench-column \{[\s\S]*height: 100%;[\s\S]*max-height: 100%;[\s\S]*overflow-y: auto;/)
    expect(content).toMatch(/\.customer-assistant-left-column,[\s\S]*\.customer-assistant-center-column,[\s\S]*\.conversation-stack \{[\s\S]*display: flex;[\s\S]*flex-direction: column;/)
    expect(content).toMatch(/\.conversation-stack \{[\s\S]*flex: 1 1 auto;[\s\S]*min-height: 0;/)
    expect(content).toMatch(/\.conversation-stack > \.conversation-panel \{[\s\S]*flex: 1 1 auto;[\s\S]*min-height: 0;/)
    expect(content).toMatch(/\.message-stream \{[\s\S]*min-height: 0;[\s\S]*max-height: none;/)
    expect(content).toMatch(/@media \(max-width: 58rem\)[\s\S]*\.customer-assistant-shell \{[\s\S]*height: calc\(100vh - 8rem\);/)
  })

  it('keeps internal task controls out of the customer lane', () => {
    const customerLane = elementByTestId(content, 'customer-conversation-lane')

    expect(customerLane).toContain('旅客')
    expect(customerLane).not.toContain('operator-task-ledger')
    expect(customerLane).not.toContain('operator-metrics-panel')
    expect(customerLane).not.toContain('confirmCustomerAssistantAction')
    expect(customerLane).not.toContain('rejectCustomerAssistantAction')
    expect(customerLane).not.toContain('确认动作')
  })

  it('uses Ant Design Vue primitives and avoids Element Plus and card nesting', () => {
    expect(content).toContain("from 'ant-design-vue'")
    expect(content).toContain("from '@ant-design/icons-vue'")
    expect(content).toContain('<a-button')
    expect(content).toContain('<a-tag')
    expect(content).toContain('<a-input')
    expect(content).not.toContain('<a-card')
    expect(regexMatches(content, /element-plus|@element-plus\/icons-vue|<el-|<\/el-|\.el-|--el-/g)).toEqual([])
  })
})
