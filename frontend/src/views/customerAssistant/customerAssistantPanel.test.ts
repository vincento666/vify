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
      'operator-metrics-panel',
      'operator-recognition-evidence-panel',
      'operator-task-ledger',
      'operator-recommendation-panel',
      'operator-advisory-evidence-panel',
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
    expect(content).toContain('data-testid="operator-progress-checklist"')
    expect(content).toContain('workspace.progressStages')
    expect(content).toContain('stage.label')
    expect(content).toContain('const expandedEventKeys = ref<string[]>([])')
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

  it('distinguishes proposed task commands from executable actions', () => {
    expect(content).toContain('isProposedTaskCommand')
    expect(content).toContain('确认任务变更')
    expect(content).toContain(`:disabled="action.status !== 'CONFIRMED' || isProposedTaskCommand(action)"`)
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

  it('renders pending proposed action edit controls in the operator panel', () => {
    const actionPanel = section(content, 'operator-proposed-actions-panel')

    expect(actionPanel).toContain('data-testid="operator-action-edit-form"')
    expect(actionPanel).toContain('startEditAction')
    expect(actionPanel).toContain('saveEditedAction')
    expect(content).toContain('updateCustomerAssistantRuntimeAction')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-action-edit-form')
  })

  it('renders configured worker profile metadata in task rows', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-task-profile"')
    expect(taskLedger).toContain('task.profile.profileId')
    expect(taskLedger).toContain('task.profile.modelPolicyRef')
    expect(taskLedger).toContain('task.profile.riskPolicyRef')
    expect(taskLedger).toContain('task.profile.toolRefs')
  })

  it('renders worker profile edit controls in the operator task ledger', () => {
    const taskLedger = section(content, 'operator-task-ledger')

    expect(taskLedger).toContain('data-testid="operator-worker-profile-edit-form"')
    expect(taskLedger).toContain('startEditWorkerProfile')
    expect(taskLedger).toContain('saveEditedWorkerProfile')
    expect(content).toContain('updateCustomerAssistantWorkerProfile')
    expect(section(content, 'customer-conversation-lane')).not.toContain('operator-worker-profile-edit-form')
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

  it('renders operator advisory knowledge evidence as a dedicated panel', () => {
    const evidencePanel = section(content, 'operator-advisory-evidence-panel')

    expect(evidencePanel).toContain('workspace.operatorAdvisoryEvidence')
    expect(evidencePanel).toContain('advisory.knowledgeSnippetCount')
    expect(evidencePanel).toContain('advisory.taskCount')
    expect(evidencePanel).toContain('advisory.warnings')
    expect(evidencePanel).toContain('operator-advisory-empty-state')
    expect(section(content, 'operator-event-timeline')).not.toContain('advisory.knowledgeSnippetCount')
  })

  it('deep-links and auto-opens seeded demo stories through the route query', () => {
    expect(content).toContain("from 'vue-router'")
    expect(content).toContain('customerAssistantStoryIdFromQuery')
    expect(content).toContain('selectCustomerAssistantDemoStoryToOpen')
    expect(content).toContain('syncSelectedDemoStoryRoute')
  })
})
