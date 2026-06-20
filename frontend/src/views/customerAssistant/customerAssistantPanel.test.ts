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

function section(content: string, testId: string) {
  const marker = `data-testid="${testId}"`
  const start = content.indexOf(marker)
  if (start < 0) return ''
  const end = content.indexOf('</section>', start)
  return end < 0 ? content.slice(start) : content.slice(start, end)
}

function betweenTestIds(content: string, startTestId: string, endTestId: string) {
  const startMarker = `data-testid="${startTestId}"`
  const endMarker = `data-testid="${endTestId}"`
  const start = content.indexOf(startMarker)
  if (start < 0) return ''
  const end = content.indexOf(endMarker, start + startMarker.length)
  return end < 0 ? content.slice(start) : content.slice(start, end)
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('CustomerAssistantPanel UI contract', () => {
  const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

  it('renders the required operator workspace regions', () => {
    for (const testId of [
      'customer-assistant-workspace',
      'customer-assistant-three-column-shell',
      'customer-assistant-left-column',
      'customer-assistant-left-tabs',
      'customer-assistant-left-session-pane',
      'customer-assistant-left-story-pane',
      'customer-assistant-center-column',
      'customer-assistant-conversation-tabs',
      'customer-assistant-ai-workbench-column',
      'customer-conversation-lane',
      'operator-conversation-lane',
      'operator-workbench-focus-pane',
      'operator-focus-sop-progress-card',
      'operator-workbench-business-pane',
      'operator-workbench-assistant-pane',
      'operator-assistant-chat-window',
      'operator-assistant-chat-header',
      'operator-assistant-chat-messages',
      'operator-assistant-event-stream',
      'operator-assistant-chat-composer',
      'operator-workbench-evidence-pane',
      'operator-workbench-config-pane',
      'operator-task-ledger',
      'operator-recommendation-panel',
      'operator-proposed-actions-panel',
      'operator-draft-panel',
      'operator-warnings-panel',
      'operator-knowledge-qa-panel',
      'operator-eval-observability-panel',
      'operator-recognition-evidence-panel',
      'operator-advisory-evidence-panel',
      'operator-audit-panel',
      'operator-worker-profile-config-panel',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
  })

  it('keeps the product shell in left center and right workbench columns', () => {
    expect(content).toMatch(
      /data-testid="customer-assistant-left-column"[\s\S]*data-testid="operator-session-inbox-dashboard"[\s\S]*data-testid="customer-assistant-demo-stories"/,
    )
    expect(content).toMatch(
      /data-testid="customer-assistant-center-column"[\s\S]*data-testid="customer-conversation-lane"[\s\S]*data-testid="operator-conversation-lane"/,
    )
    expect(content).toMatch(
      /data-testid="customer-assistant-ai-workbench-column"[\s\S]*data-testid="operator-ai-workbench-tabs"[\s\S]*data-testid="operator-workbench-focus-pane"[\s\S]*data-testid="operator-workbench-config-pane"/,
    )
    expect(section(content, 'customer-assistant-center-column')).not.toContain('operator-task-ledger')
    expect(section(content, 'customer-assistant-center-column')).not.toContain('operator-worker-profile-config-panel')
  })

  it('uses tabs to switch between focus, assistant, business, evidence, and config panes', () => {
    expect(content).toContain(
      "const activeWorkbenchTab = ref<'focus' | 'assistant' | 'business' | 'evidence' | 'config'>('focus')",
    )
    expect(content).toContain('data-testid="operator-ai-workbench-tabs"')
    expect(content).toContain('聚焦')
    expect(content).toContain('AI助手')
    expect(content).toContain('办理')
    expect(content).toContain('证据')
    expect(content).toContain('配置')
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'focus'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'assistant'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'business'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'evidence'\"")
    expect(content).toContain("v-show=\"activeWorkbenchTab === 'config'\"")
    expect(content).not.toContain("activeWorkbenchTab === 'overview'")
    expect(content).not.toContain("activeWorkbenchTab === 'tasks'")
    expect(content).not.toContain("activeWorkbenchTab === 'audit'")
  })

  it('defaults the right workbench to business focus and keeps technical panels out of the default pane', () => {
    const focusPane = betweenTestIds(content, 'operator-workbench-focus-pane', 'operator-workbench-business-pane')

    expect(focusPane).toContain('data-testid="operator-focus-intent-card"')
    expect(focusPane).toContain('data-testid="operator-focus-script-card"')
    expect(focusPane).toContain('data-testid="operator-focus-sop-progress-card"')
    expect(focusPane).toContain('data-testid="operator-confirmation-cards"')
    expect(focusPane).toContain('意图识别')
    expect(focusPane).toContain('情绪识别')
    expect(focusPane).toContain('业务办理指引')
    expect(focusPane).toContain('话术推荐')
    expect(focusPane).toContain('SOP办理进度')
    expect(focusPane).toContain('workspace.taskSummary.items')
    expect(focusPane).toContain('业务办理确认')
    expect(focusPane).not.toContain('data-testid="operator-task-ledger"')
    expect(focusPane).not.toContain('data-testid="operator-progress-checklist"')
    expect(focusPane).not.toContain('data-testid="operator-worker-async-refs-panel"')
    expect(focusPane).not.toContain('data-testid="operator-knowledge-qa-panel"')
    expect(focusPane).not.toContain('data-testid="operator-event-timeline"')
    expect(focusPane).not.toContain('data-testid="operator-worker-profile-config-panel"')
    expect(focusPane).not.toContain('modelPolicyRef')
    expect(focusPane).not.toContain('promptRef')
    expect(focusPane).not.toContain('workerRunId')
    expect(focusPane).not.toContain('Worker 配置')
  })

  it('renders the assistant tab as one conversational AI workbench window', () => {
    const assistantPane = betweenTestIds(content, 'operator-workbench-assistant-pane', 'operator-workbench-evidence-pane')
    const chatWindow = betweenTestIds(content, 'operator-assistant-chat-window', 'operator-workbench-evidence-pane')

    expect(assistantPane).toMatch(
      /data-testid="operator-workbench-assistant-pane"[\s\S]*data-testid="operator-assistant-chat-window"[\s\S]*data-testid="operator-assistant-chat-composer"/,
    )
    expect(chatWindow).toContain('class="assistant-chat-window"')
    expect(chatWindow).toContain('data-testid="operator-assistant-chat-header"')
    expect(chatWindow).toContain('data-testid="operator-assistant-chat-messages"')
    expect(chatWindow).toContain('data-testid="operator-assistant-event-stream"')
    expect(chatWindow).toContain('data-testid="operator-assistant-chat-composer"')
    expect(chatWindow).toContain('data-testid="operator-knowledge-qa-panel"')
    expect(chatWindow).toContain('assistant-message assistant-message--assistant')
    expect(assistantPane).toContain('askOperatorKnowledgeQuestion')
    expect(assistantPane).not.toContain('data-testid="operator-progress-checklist"')
    expect(assistantPane).not.toContain('data-testid="operator-sub-agent-control"')
    expect(assistantPane).not.toContain('data-testid="operator-metrics-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-worker-async-refs-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-event-timeline"')
    expect(assistantPane).not.toContain('data-testid="operator-confirmation-cards"')
    expect(assistantPane).not.toContain('workspace.proposedActions')
    expect(assistantPane).not.toContain('workspace.progressStages')
    expect(assistantPane).not.toContain('workerRefreshLoadingTaskId')
    expect(assistantPane).not.toContain('cancelWorkerRun')
    expect(assistantPane).not.toContain('data-testid="operator-eval-observability-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-recognition-evidence-panel"')
    expect(assistantPane).not.toContain('data-testid="operator-task-ledger"')
    expect(assistantPane).not.toContain('data-testid="operator-worker-profile-config-panel"')
  })

  it('keeps full task handling in the business tab while sharing confirmation card state', () => {
    const focusPane = betweenTestIds(content, 'operator-workbench-focus-pane', 'operator-workbench-business-pane')
    const businessPane = betweenTestIds(content, 'operator-workbench-business-pane', 'operator-workbench-assistant-pane')
    const assistantPane = betweenTestIds(content, 'operator-workbench-assistant-pane', 'operator-workbench-evidence-pane')

    expect(businessPane).toContain('data-testid="operator-task-ledger"')
    expect(businessPane).toContain('data-testid="operator-recommendation-panel"')
    expect(businessPane).toContain('data-testid="operator-proposed-actions-panel"')
    expect(businessPane).toContain('data-testid="operator-draft-panel"')
    expect(businessPane).toContain('data-testid="operator-warnings-panel"')
    expect(businessPane).toContain('data-testid="operator-task-controls"')
    expect(businessPane).not.toContain('data-testid="operator-worker-async-refs"')
    expect(businessPane).not.toContain('modelPolicyRef')
    expect(businessPane).not.toContain('promptRef')
    expect(focusPane).toContain('workspace.proposedActions')
    expect(assistantPane).not.toContain('workspace.proposedActions')
    expect(businessPane).toContain('workspace.proposedActions')
  })

  it('keeps the config tab for worker profile configuration', () => {
    const configPane = section(content, 'operator-workbench-config-pane')

    expect(configPane).toContain('data-testid="operator-worker-profile-config-panel"')
    expect(configPane).toContain('workerProfiles')
    expect(configPane).toContain('profile.taskType')
    expect(configPane).toContain('profile.taskKey')
    expect(configPane).toContain('profile.workerType')
    expect(configPane).toContain('profile.workerRef')
    expect(configPane).toContain('profile.modelPolicyRef')
    expect(configPane).toContain('profile.promptRef')
    expect(configPane).toContain('profile.toolPolicyRef')
    expect(configPane).toContain('profile.riskPolicyRef')
    expect(configPane).toContain('profile.outputSchemaRef')
    expect(configPane).toContain('operator-worker-profile-catalog-edit-form')
    expect(configPane).toContain('startEditWorkerProfileCatalog')
    expect(configPane).toContain('saveEditedWorkerProfile')
    expect(content).toContain('updateCustomerAssistantWorkerProfile')
  })

  it('keeps the center operator lane passenger-facing and free of assistant tooling', () => {
    const centerColumn = section(content, 'customer-assistant-center-column')
    const operatorLane = section(content, 'operator-conversation-lane')

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
    const customerLane = section(content, 'customer-conversation-lane')

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

  it('does not seed the production panel with mock runtime data', () => {
    expect(content).not.toContain('mockCustomerAssistantTurnResult')
    expect(content).not.toContain('customerAssistantFixtures')
    expect(content).not.toContain('Mock Runtime')
    expect(content).toContain('createCustomerAssistantRuntimeState()')
  })

  it('renders draft delivery controls only in the operator proposed-action panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('deliverAction(action.id)')
    expect(actionPanel).toContain('isDeliverableDraftAction(action)')
    expect(actionPanel).toContain('外发草稿')
    expect(actionPanel).toContain('operator-draft-delivery-receipt')
    expect(actionPanel).toContain('receipt.visible && !isCustomerReplyDraftAction(action)')
    expect(section(content, 'customer-conversation-lane')).not.toContain('外发草稿')
  })

  it('keeps observability metrics out of the assistant chat tab', () => {
    const assistantPane = betweenTestIds(content, 'operator-workbench-assistant-pane', 'operator-workbench-evidence-pane')
    const evidencePane = betweenTestIds(content, 'operator-workbench-evidence-pane', 'operator-workbench-config-pane')

    expect(assistantPane).not.toContain('metricsSummary.tiles')
    expect(assistantPane).not.toContain('metricsSummary.failures')
    expect(assistantPane).not.toContain('人工采纳率')
    expect(evidencePane).toContain('evalSurface.tiles')
    expect(evidencePane).not.toContain('compactPayload')
  })

  it('renders task controls in the business ledger and keeps worker refs out of the default pane', () => {
    const businessPane = betweenTestIds(content, 'operator-workbench-business-pane', 'operator-workbench-assistant-pane')

    expect(businessPane).toContain('data-testid="operator-task-controls"')
    expect(businessPane).toContain('proposeTaskControl')
    expect(businessPane).toContain('重试')
    expect(businessPane).toContain('取消')
    expect(businessPane).toContain('恢复')
    expect(businessPane).not.toContain('workerRunId')
    expect(businessPane).not.toContain('modelPolicyRef')
    expect(businessPane).not.toContain('promptRef')
    expect(businessPane).not.toContain('refreshWorkerResults')
    expect(businessPane).not.toContain('cancelWorkerRun')
  })

  it('renders action execution and decision receipts in the business panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-receipt"')
    expect(actionPanel).toContain('data-testid="operator-action-decision-receipt"')
    expect(actionPanel).toContain('formatCustomerAssistantActionReceipt(action)')
    expect(actionPanel).toContain('formatCustomerAssistantActionDecisionReceipt(action)')
    expect(actionPanel).toContain('decisionReceipt.note')
    expect(actionPanel).toContain('decisionReceipt.reason')
    expect(actionPanel).toContain('执行回执')
    expect(actionPanel).toContain('决策回执')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-action-decision-receipt')
  })

  it('renders the seeded session inbox as an operator dashboard outside the customer lane', () => {
    const inboxPanel = section(content, 'operator-session-inbox-dashboard')

    expect(inboxPanel).toContain('sessionInboxRows')
    expect(inboxPanel).toContain('openSessionInboxRow')
    expect(inboxPanel).toContain('data-testid="operator-session-inbox-row"')
    expect(inboxPanel).toContain('row.customerName')
    expect(inboxPanel).toContain('row.storyTitle')
    expect(inboxPanel).toContain('row.statusLabel')
    expect(inboxPanel).toContain('row.lastActivityLabel')
    expect(inboxPanel).toContain('多客户会话')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-session-inbox-dashboard')
    expect(section(content, 'customer-conversation-lane')).not.toContain('openSessionInboxRow')
  })

  it('renders the worker profile catalog as a dedicated config panel', () => {
    const configPane = section(content, 'operator-workbench-config-pane')

    expect(configPane).toContain('workerProfiles')
    expect(configPane).toContain('profile.taskType')
    expect(configPane).toContain('profile.taskKey')
    expect(configPane).toContain('profile.workerType')
    expect(configPane).toContain('profile.workerRef')
    expect(configPane).toContain('profile.modelPolicyRef')
    expect(configPane).toContain('profile.promptRef')
    expect(configPane).toContain('profile.toolRefs')
    expect(configPane).toContain('profile.toolPolicyRef')
    expect(configPane).toContain('profile.riskPolicyRef')
    expect(configPane).toContain('profile.outputSchemaRef')
    expect(configPane).toContain('startEditWorkerProfileCatalog')
    expect(configPane).toContain('saveEditedWorkerProfile')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-worker-profile-config-panel')
  })

  it('keeps worker async refs and evidence outside the assistant chat tab', () => {
    const assistantPane = betweenTestIds(content, 'operator-workbench-assistant-pane', 'operator-workbench-evidence-pane')
    const evidencePane = betweenTestIds(content, 'operator-workbench-evidence-pane', 'operator-workbench-config-pane')

    expect(assistantPane).not.toContain('data-testid="operator-worker-async-refs"')
    expect(assistantPane).not.toContain('workerRefreshLoadingTaskId')
    expect(assistantPane).not.toContain('refreshWorkerResults')
    expect(assistantPane).not.toContain('cancelWorkerRun')
    expect(assistantPane).toContain('askOperatorKnowledgeQuestion')
    expect(assistantPane).toContain('operatorKnowledgeQa.sourceRows')
    expect(assistantPane).toContain('operatorKnowledgeQa.evidenceRows')
    expect(assistantPane).not.toContain('data-testid="operator-confirmation-cards"')
    expect(evidencePane).toContain('evalSurface.workerExecution')
    expect(evidencePane).toContain('workspace.operatorAdvisoryEvidence')
    expect(evidencePane).toContain('workspace.operatorAuditRows')
  })

  it('deep-links and auto-opens seeded demo stories through the route query', () => {
    expect(content).toContain("from 'vue-router'")
    expect(content).toContain('customerAssistantStoryIdFromQuery')
    expect(content).toContain('selectCustomerAssistantDemoStoryToOpen')
    expect(content).toContain('syncSelectedDemoStoryRoute')
  })
})
