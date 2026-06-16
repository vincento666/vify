import type { AgentPreviewRunDebugDetail } from '@/api/agent'

export type AgentDebugTrace = {
  keyword: string
  elapsedMs: number
  firstResponseMs: number
  latencyMs: number
  inputChars: number
  outputChars: number
  status: string
  finishReason: string
  runId: string
  startedAtText: string
  nodes: Array<Record<string, any>>
  axisTicks: number[]
  flameLanes: Array<Record<string, any>>
}

export function summarizeAgentPreviewRunDebug(detail: AgentPreviewRunDebugDetail | null | undefined) {
  return {
    runLabel: detail?.previewRunId ? `Preview Run #${detail.previewRunId}` : 'Preview Run',
    statusLabel: String(detail?.status || '等待运行'),
    charsLabel: `输入 ${Number(detail?.inputChars || 0)} 字 / 输出 ${Number(detail?.outputChars || 0)} 字`,
  }
}

export function buildAgentPreviewDebugTrace(detail: AgentPreviewRunDebugDetail | null | undefined): AgentDebugTrace | null {
  if (!detail) return null
  return {
    keyword: String(detail.input?.content || 'preview'),
    elapsedMs: Number(detail.elapsedMs || 0),
    firstResponseMs: Number(detail.firstResponseMs || 0),
    latencyMs: Number(detail.latencyMs || 0),
    inputChars: Number(detail.inputChars || 0),
    outputChars: Number(detail.outputChars || 0),
    status: String(detail.status || '成功'),
    finishReason: String(detail.finishReason || 'stop'),
    runId: String(detail.previewRunId || detail.sessionId || ''),
    startedAtText: formatDebugTime(detail.startedAt),
    nodes: Array.isArray(detail.nodes) ? detail.nodes : [],
    axisTicks: Array.isArray(detail.axisTicks) ? detail.axisTicks : [],
    flameLanes: Array.isArray(detail.flameLanes) ? detail.flameLanes : [],
  }
}

function formatDebugTime(value?: string) {
  if (!value) return '暂无'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
