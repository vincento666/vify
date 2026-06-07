import type { RuntimeLabTask, RuntimeLabTurn } from '@/api/runtimeLab'

export interface AirlineSopScenario {
  id: string
  label: string
  shortLabel: string
  startMessage: string
  sampleReplies: string[]
}

export interface RuntimeLabTranscriptRow {
  id: string
  role: 'user' | 'assistant'
  content: string
  routeAction?: string
  targetSopId?: string | null
  taskSummary?: string
  resumePrompt?: string
}

export const AIRLINE_SOP_SCENARIOS: AirlineSopScenario[] = [
  {
    id: 'refund_ticket',
    label: '退票办理',
    shortLabel: '退票',
    startMessage: '我要退票',
    sampleReplies: ['手机号 13800138000', '确认', '继续退票'],
  },
  {
    id: 'change_flight',
    label: '改签办理',
    shortLabel: '改签',
    startMessage: '我要改签航班',
    sampleReplies: ['手机号 13800138000', '确认', '继续改签'],
  },
  {
    id: 'invoice_apply',
    label: '发票申请',
    shortLabel: '发票',
    startMessage: '我要开发票',
    sampleReplies: ['手机号 13800138000', '确认', '继续发票申请'],
  },
  {
    id: 'baggage_service',
    label: '行李服务',
    shortLabel: '行李',
    startMessage: '我要办理行李服务',
    sampleReplies: ['手机号 13800138000', '确认', '继续行李服务'],
  },
  {
    id: 'seat_checkin',
    label: '值机选座',
    shortLabel: '选座',
    startMessage: '我要值机选座',
    sampleReplies: ['手机号 13800138000', '确认', '继续值机选座'],
  },
]

export function getAirlineSopScenario(id: string) {
  return AIRLINE_SOP_SCENARIOS.find((scenario) => scenario.id === id) ?? null
}

export function buildUserTranscriptRow(id: string, content: string): RuntimeLabTranscriptRow {
  return {
    id,
    role: 'user',
    content,
  }
}

export function buildRuntimeLabTranscriptRow(turn: RuntimeLabTurn): RuntimeLabTranscriptRow {
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: turn.reply,
    routeAction: turn.routeDecision.action,
    targetSopId: turn.routeDecision.targetSopId,
    taskSummary: summarizeTasks(turn.activeTask, turn.suspendedTasks),
    resumePrompt: typeof turn.resumeOffer?.prompt === 'string' ? turn.resumeOffer.prompt : undefined,
  }
}

export function summarizeTasks(activeTask: RuntimeLabTask | null, suspendedTasks: RuntimeLabTask[]) {
  const chunks: string[] = []
  if (activeTask) chunks.push(`active: ${activeTask.sopId}`)
  if (suspendedTasks.length) chunks.push(`suspended: ${suspendedTasks.map((task) => task.sopId).join(', ')}`)
  return chunks.join(' | ') || 'no active task'
}
