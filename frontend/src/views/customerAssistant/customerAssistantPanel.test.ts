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

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('CustomerAssistantPanel UI contract', () => {
  const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

  it('renders the required operator workspace regions', () => {
    for (const testId of [
      'customer-assistant-workspace',
      'customer-conversation-lane',
      'operator-conversation-lane',
      'operator-progress-checklist',
      'operator-sub-agent-control',
      'operator-metrics-panel',
      'operator-recognition-evidence-panel',
      'operator-knowledge-qa-panel',
      'operator-task-ledger',
      'operator-recommendation-panel',
      'operator-advisory-evidence-panel',
      'operator-audit-panel',
      'operator-draft-panel',
      'operator-proposed-actions-panel',
      'operator-event-timeline',
      'operator-warnings-panel',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
  })

  it('keeps internal task controls out of the customer lane', () => {
    const customerLane = section(content, 'customer-conversation-lane')

    expect(customerLane).toContain('客户侧')
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

  it('renders progress checklist and keeps timeline collapsed by default', () => {
    const progressPanel = section(content, 'operator-progress-checklist')

    expect(progressPanel).toContain('data-testid="operator-sub-agent-control"')
    expect(progressPanel).toContain('workspace.progressStages')
    expect(progressPanel).toContain('stage.label')
    expect(progressPanel).toContain('spawnSubAgent')
    expect(progressPanel).toContain('subAgentLoading')
    expect(progressPanel).toContain('subAgentStatusLabel')
    expect(content).toContain('const expandedEventKeys = ref<string[]>([])')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-sub-agent-control')
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

  it('renders observability metrics in the operator panel without raw payload details', () => {
    const metricsPanel = section(content, 'operator-metrics-panel')

    expect(metricsPanel).toContain('metricsSummary.tiles')
    expect(metricsPanel).toContain('metricsSummary.failures')
    expect(metricsPanel).toContain('人工采纳率')
    expect(metricsPanel).not.toContain('compactPayload')
  })

  it('renders aggregate seeded demo metrics above the story picker', () => {
    const storyStrip = section(content, 'customer-assistant-demo-stories')

    expect(storyStrip).toContain('data-testid="customer-assistant-demo-metrics"')
    expect(storyStrip).toContain('demoStoryMetricsSummary.tiles')
    expect(storyStrip).toContain('演示总览')
    expect(content).toContain('loadDemoStoryMetrics')
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

  it('distinguishes proposed task commands from executable actions', () => {
    expect(content).toContain('isProposedTaskCommand')
    expect(content).toContain('isCustomerReplyDraftAction')
    expect(content).toContain('确认任务变更')
    expect(content).toContain(
      `:disabled="action.status !== 'CONFIRMED' || isProposedTaskCommand(action) || isCustomerReplyDraftAction(action)"`,
    )
  })

  it('renders action execution receipts in the operator proposed-action panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-receipt"')
    expect(actionPanel).toContain('formatCustomerAssistantActionReceipt(action)')
    expect(actionPanel).toContain('receipt.auditRows')
    expect(actionPanel).toContain('执行回执')
  })

  it('renders action decision receipts in the operator proposed-action panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-decision-receipt"')
    expect(actionPanel).toContain('formatCustomerAssistantActionDecisionReceipt(action)')
    expect(actionPanel).toContain('decisionReceipt.note')
    expect(actionPanel).toContain('decisionReceipt.reason')
    expect(actionPanel).toContain('决策回执')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-action-decision-receipt')
  })

  it('renders retry cancel and resume task controls in the operator ledger', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-task-controls"')
    expect(taskLedger).toContain('proposeTaskControl')
    expect(taskLedger).toContain('重试')
    expect(taskLedger).toContain('取消')
    expect(taskLedger).toContain('恢复')
    expect(section(content, 'customer-conversation-lane')).not.toContain('proposeTaskControl')
  })

  it('renders pending worker refs and manual refresh controls in the operator ledger', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-worker-async-refs"')
    expect(taskLedger).toContain('task.workerAsyncRefs.workerRunId')
    expect(taskLedger).toContain('refreshWorkerResults')
    expect(taskLedger).toContain('刷新结果')
  })

  it('renders pending proposed action edit controls in the operator panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-edit-form"')
    expect(actionPanel).toContain('startEditAction')
    expect(actionPanel).toContain('saveEditedAction')
    expect(content).toContain('updateCustomerAssistantRuntimeAction')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-action-edit-form')
  })

  it('renders decision note controls in pending operator proposed-action rows', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-decision-form"')
    expect(actionPanel).toContain('aria-label="确认备注"')
    expect(actionPanel).toContain('aria-label="拒绝原因"')
    expect(actionPanel).toContain('actionDecisionDraft(action.id).confirmNote')
    expect(actionPanel).toContain('actionDecisionDraft(action.id).rejectReason')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-action-decision-form')
  })

  it('renders configured worker profile metadata in task rows', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-task-profile"')
    expect(taskLedger).toContain('task.profile.profileId')
    expect(taskLedger).toContain('task.profile.modelPolicyRef')
    expect(taskLedger).toContain('task.profile.riskPolicyRef')
    expect(taskLedger).toContain('task.profile.toolRefs')
  })

  it('renders the configured worker profile catalog as a dedicated operator panel', () => {
    const profilePanel = section(content, 'operator-worker-profile-config-panel')

    expect(profilePanel).toContain('workerProfiles')
    expect(profilePanel).toContain('profile.taskType')
    expect(profilePanel).toContain('profile.taskKey')
    expect(profilePanel).toContain('profile.workerType')
    expect(profilePanel).toContain('profile.workerRef')
    expect(profilePanel).toContain('profile.modelPolicyRef')
    expect(profilePanel).toContain('profile.promptRef')
    expect(profilePanel).toContain('profile.toolRefs')
    expect(profilePanel).toContain('profile.riskPolicyRef')
    expect(profilePanel).toContain('startEditWorkerProfile')
    expect(profilePanel).toContain('saveEditedWorkerProfile')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-worker-profile-config-panel')
  })

  it('renders worker profile edit controls in the operator task ledger', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-worker-profile-edit-form"')
    expect(taskLedger).toContain('startEditWorkerProfile')
    expect(taskLedger).toContain('saveEditedWorkerProfile')
    expect(content).toContain('updateCustomerAssistantWorkerProfile')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-worker-profile-edit-form')
  })

  it('renders the eval observability surface as a dedicated read-only panel', () => {
    const evalPanel = section(content, 'operator-eval-observability-panel')

    expect(evalPanel).toContain('evalSurface.tiles')
    expect(evalPanel).toContain('evalSurface.taskRecognition')
    expect(evalPanel).toContain('evalSurface.workerExecution')
    expect(evalPanel).toContain('evalSurface.modelEvidence')
    expect(evalPanel).toContain('evalSurface.failures')
    expect(evalPanel).toContain('任务识别')
    expect(evalPanel).toContain('Worker 执行')
    expect(evalPanel).toContain('模型/回退证据')
    expect(content).toContain('formatCustomerAssistantEvalSurface')
    expect(section(content, 'operator-event-timeline')).not.toContain('evalSurface.modelEvidence')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-eval-observability-panel')
  })

  it('renders task recognition evidence as a dedicated operator panel', () => {
    const evidencePanel = section(content, 'operator-recognition-evidence-panel')

    expect(evidencePanel).toContain('workspace.recognitionEvidence')
    expect(evidencePanel).toContain('recognition.profileId')
    expect(evidencePanel).toContain('recognition.modelPolicyRef')
    expect(evidencePanel).toContain('recognition.riskPolicyRef')
    expect(evidencePanel).toContain('operator-recognition-empty-state')
    expect(section(content, 'operator-event-timeline')).not.toContain('recognition.profileId')
  })

  it('renders operator knowledge Q&A as a dedicated compact panel', () => {
    const qaPanel = section(content, 'operator-knowledge-qa-panel')

    expect(qaPanel).toContain('operatorKnowledgeQuestion')
    expect(qaPanel).toContain('askOperatorKnowledgeQuestion')
    expect(qaPanel).toContain('operatorKnowledgeQa.sourceRows')
    expect(qaPanel).toContain('operatorKnowledgeQa.evidenceRows')
    expect(qaPanel).toContain('operatorKnowledgeQa.contextRows')
    expect(qaPanel).toContain('operatorKnowledgeQa.warnings')
    expect(qaPanel).toContain('data-testid="operator-knowledge-qa-answer"')
    expect(qaPanel).toContain('data-testid="operator-knowledge-qa-source"')
    expect(qaPanel).toContain('data-testid="operator-knowledge-qa-evidence"')
    expect(qaPanel).not.toContain('JSON.stringify')
    expect(qaPanel).not.toContain('compactPayload')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-knowledge-qa-panel')
  })

  it('renders operator advisory knowledge evidence as a dedicated panel', () => {
    const evidencePanel = section(content, 'operator-advisory-evidence-panel')

    expect(evidencePanel).toContain('workspace.operatorAdvisoryEvidence')
    expect(evidencePanel).toContain('advisory.knowledgeSnippetCount')
    expect(evidencePanel).toContain('advisory.taskCount')
    expect(evidencePanel).toContain('advisory.warnings')
    expect(evidencePanel).toContain('operator-advisory-empty-state')
    expect(section(content, 'operator-event-timeline')).not.toContain('advisory.knowledgeSnippetCount')
  })

  it('renders operator audit rows as a compact read-only panel', () => {
    const auditPanel = section(content, 'operator-audit-panel')

    expect(auditPanel).toContain('workspace.operatorAuditRows')
    expect(auditPanel).toContain('audit.summary')
    expect(auditPanel).toContain('audit.targetLabel')
    expect(auditPanel).toContain('operator-audit-empty-state')
    expect(auditPanel).not.toContain('compactPayload')
  })

  it('deep-links and auto-opens seeded demo stories through the route query', () => {
    expect(content).toContain("from 'vue-router'")
    expect(content).toContain('customerAssistantStoryIdFromQuery')
    expect(content).toContain('selectCustomerAssistantDemoStoryToOpen')
    expect(content).toContain('syncSelectedDemoStoryRoute')
  })
})
