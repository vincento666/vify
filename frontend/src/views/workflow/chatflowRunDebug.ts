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
