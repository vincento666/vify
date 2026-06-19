import {
  buildWorkflowRunCallTree,
  buildWorkflowRunFlamegraph,
  type WorkflowRunCallTreeRow,
  type WorkflowRunDebugDetail,
  type WorkflowRunFlamegraphRow,
  type WorkflowRunNodeDetail,
} from './workflowRunDebug'

export type ChatflowRunDebugDetail = WorkflowRunDebugDetail & {
  session?: {
    sessionId?: string
    conversationId?: string
    userId?: string
    channel?: string
    status?: string
    currentRunId?: number
  }
  variables?: Record<string, any>
  events?: any[]
  streamEvents?: any[]
  waitingEvent?: any
  checkpoint?: any
}

export type ChatflowSessionDebugState = NonNullable<ChatflowRunDebugDetail['session']> & {
  variables?: Record<string, any>
  waitingEvent?: any
  checkpoint?: any
}

export type ChatflowRunSummary = {
  runLabel: string
  statusLabel: string
  sessionLabel: string
  nodeCountLabel: string
}

export function summarizeChatflowRunDebug(detail: ChatflowRunDebugDetail | null | undefined): ChatflowRunSummary {
  const nodeCount = Array.isArray(detail?.nodeDetails) ? detail.nodeDetails.length : 0
  return {
    runLabel: detail?.runId ? `Run #${detail.runId}` : '尚未运行',
    statusLabel: String(detail?.status || detail?.session?.status || '等待试运行'),
    sessionLabel: [
      detail?.session?.conversationId,
      detail?.session?.userId,
      detail?.session?.channel,
    ].filter(Boolean).join(' · ') || '暂无会话',
    nodeCountLabel: `${nodeCount} ${nodeCount === 1 ? 'node' : 'nodes'}`,
  }
}

export function buildChatflowRunCallTree(detail: ChatflowRunDebugDetail | null | undefined): WorkflowRunCallTreeRow[] {
  return buildWorkflowRunCallTree(detail)
}

export function buildChatflowRunFlamegraph(detail: ChatflowRunDebugDetail | null | undefined): WorkflowRunFlamegraphRow[] {
  return buildWorkflowRunFlamegraph(detail)
}

export function chatflowRunNodeDetails(detail: ChatflowRunDebugDetail | null | undefined): WorkflowRunNodeDetail[] {
  return Array.isArray(detail?.nodeDetails) ? detail.nodeDetails : []
}

export function projectRuntimeV2ChatflowSessionState(
  run: Record<string, any>,
  status: unknown,
  previous: ChatflowSessionDebugState | null | undefined = null,
): ChatflowSessionDebugState {
  const checkpoint = run.checkpoint || previous?.checkpoint || null
  const normalizedStatus = String(status || run.status || '').trim().toUpperCase()
  const sessionStatus = checkpoint && ['INTERRUPTED', 'WAITING'].includes(normalizedStatus)
    ? 'waiting'
    : normalizeSessionStatus(normalizedStatus)
  const sessionId = String(run.sessionId || previous?.sessionId || run.session_id || '')
  return {
    ...(previous || {}),
    sessionId,
    conversationId: String(run.conversationId || previous?.conversationId || sessionId),
    userId: String(run.userId || previous?.userId || ''),
    channel: String(run.channel || previous?.channel || ''),
    status: sessionStatus,
    currentRunId: Number(run.runId || previous?.currentRunId || 0),
    variables: isRecord(run.variables) ? run.variables : previous?.variables || {},
    waitingEvent: run.waitingEvent || previous?.waitingEvent || null,
    checkpoint,
  }
}

export function withChatflowSessionState(
  detail: ChatflowRunDebugDetail,
  session: ChatflowSessionDebugState | null | undefined,
): ChatflowRunDebugDetail {
  if (!session) return detail
  return {
    ...detail,
    session,
    variables: session.variables || {},
    waitingEvent: session.waitingEvent || null,
    checkpoint: session.checkpoint || null,
  }
}

function normalizeSessionStatus(status: string) {
  if (status === 'SUCCEEDED' || status === 'COMPLETED') return 'completed'
  if (status === 'CANCELLED' || status === 'CANCELED') return 'cancelled'
  if (status === 'FAILED') return 'failed'
  if (status === 'RUNNING') return 'running'
  if (status === 'INTERRUPTED' || status === 'WAITING') return 'waiting'
  return status.toLowerCase()
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}
