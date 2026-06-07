export type ChatflowEventLike = {
  id?: number
  sequence?: number
  type?: string
  nodeKey?: string
  payload?: Record<string, any>
  checkpointId?: number | null
  createdAt?: string
}

export type ChatflowTimelineItem = {
  id: number
  sequence: number
  type: string
  label: string
  nodeKey: string
  content: string
  meta: string
  createdAt: string
}

export type ChatflowVariableRow = {
  scope: string
  name: string
  value: string
}

export type ChatflowResumeField = {
  key: string
  label: string
  placeholder: string
}

const EVENT_LABELS: Record<string, string> = {
  message: '消息',
  interrupt: '等待输入',
  resume: '继续执行',
  done: '完成',
  error: '错误',
  tool_call: '工具调用',
  node_started: '节点开始',
  node_completed: '节点完成',
  handoff_requested: '转人工',
}

const VARIABLE_SCOPE_ORDER = ['conversation', 'sys', 'user', 'channel', 'global', 'flow', 'input', 'external']

export function formatChatflowTimeline(events: ChatflowEventLike[]): ChatflowTimelineItem[] {
  return [...events]
    .sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0))
    .map((event) => {
      const type = String(event.type || '')
      const checkpoint = event.checkpointId ? `Checkpoint #${event.checkpointId}` : ''
      const nodeKey = String(event.nodeKey || event.payload?.nodeKey || '')
      return {
        id: Number(event.id || 0),
        sequence: Number(event.sequence || 0),
        type,
        label: EVENT_LABELS[type] || type || '事件',
        nodeKey,
        content: eventContent(event),
        meta: [nodeKey ? `Node ${nodeKey}` : '', checkpoint].filter(Boolean).join(' · '),
        createdAt: String(event.createdAt || ''),
      }
    })
}

export function flattenChatflowVariables(variables: Record<string, any> | null | undefined): ChatflowVariableRow[] {
  if (!variables || typeof variables !== 'object') return []
  const scopes = Object.keys(variables).sort((left, right) => {
    const leftIndex = VARIABLE_SCOPE_ORDER.indexOf(left)
    const rightIndex = VARIABLE_SCOPE_ORDER.indexOf(right)
    return (leftIndex === -1 ? 999 : leftIndex) - (rightIndex === -1 ? 999 : rightIndex) || left.localeCompare(right)
  })
  const rows: ChatflowVariableRow[] = []
  for (const scope of scopes) {
    const values = variables[scope]
    if (!values || typeof values !== 'object' || Array.isArray(values)) continue
    for (const name of Object.keys(values).sort()) {
      rows.push({
        scope,
        name,
        value: formatVariableValue(values[name]),
      })
    }
  }
  return rows
}

export function buildChatflowResumeFields(schema: Record<string, any> | null | undefined): ChatflowResumeField[] {
  const type = String(schema?.type || '').toUpperCase()
  if (type === 'HUMAN_INPUT') {
    const approvalMode = String(schema?.approvalMode || '').toLowerCase()
    if (approvalMode === 'approval') {
      return [
        { key: 'approved', label: '审批结果', placeholder: 'true / false' },
        { key: 'payload', label: '补充数据', placeholder: 'JSON 或文本' },
      ]
    }
    return [{ key: 'payload', label: '人工输入', placeholder: '输入人工处理结果' }]
  }
  if (type === 'INFORMATION_COLLECTION') {
    const missing = Array.isArray(schema?.missing) ? schema.missing.join(', ') : '缺失字段'
    return [{ key: 'answer', label: '补充信息', placeholder: `补充 ${missing}` }]
  }
  return [{ key: 'answer', label: '回复内容', placeholder: '输入回复内容' }]
}

function eventContent(event: ChatflowEventLike): string {
  const payload = event.payload || {}
  if (event.type === 'handoff_requested') {
    return [
      payload.handoffId ? `工单 #${payload.handoffId}` : '',
      payload.queue,
      payload.status,
    ].filter(Boolean).join(' · ')
  }
  if (typeof payload.content === 'string') return payload.content
  if (payload.output) return formatVariableValue(payload.output)
  if (payload.resumeData) return formatVariableValue(payload.resumeData)
  if (payload.question) return String(payload.question)
  if (payload.followup) return String(payload.followup)
  return ''
}

function formatVariableValue(value: any): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}
