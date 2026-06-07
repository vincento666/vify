import type { WorkflowCanvasNodeType } from './flowGraph'

export type NodePaletteMode = 'workflow' | 'chatflow'

export interface NodePaletteEntry {
  type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>
  label: string
  searchTerms?: string[]
  modes?: NodePaletteMode[]
  disabled?: boolean
}

export interface NodePaletteGroup {
  title: string
  items: NodePaletteEntry[]
}

const COZE_NODE_PALETTE_GROUPS: NodePaletteGroup[] = [
  {
    title: '资源',
    items: [
      { type: 'LLM', label: '大模型', searchTerms: ['model', 'llm'] },
      { type: 'TOOL_CALL', label: '插件', searchTerms: ['工具调用', 'tool', 'mcp'] },
      { type: 'EXECUTE_WORKFLOW', label: '工作流', searchTerms: ['子工作流', 'subworkflow'] },
      { type: 'API_CALL', label: 'API 调用', searchTerms: ['http', '接口'] },
      { type: 'AGENT_CALL', label: '智能体', searchTerms: ['agent'] },
    ],
  },
  {
    title: '业务逻辑',
    items: [
      { type: 'CODE', label: '代码', searchTerms: ['python'] },
      { type: 'CONDITION', label: '选择器', searchTerms: ['条件', 'condition', 'if'] },
      { type: 'INTENT_RECOGNITION', label: '意图识别', searchTerms: ['意图', 'intent'] },
      { type: 'TEXT_PROCESS', label: '文本处理', searchTerms: ['文本', 'text'] },
      { type: 'JSON_PARSE', label: 'JSON 解析', searchTerms: ['json'] },
      { type: 'VARIABLE_AGGREGATION', label: '变量聚合', searchTerms: ['聚合'] },
      { type: 'VARIABLE_ASSIGN', label: '变量赋值', searchTerms: ['赋值'] },
    ],
  },
  {
    title: '输入&输出',
    items: [
      { type: 'MESSAGE', label: '消息', searchTerms: ['message'] },
      { type: 'QUESTION', label: '问题', searchTerms: ['question'] },
      { type: 'INFORMATION_COLLECTION', label: '信息收集', searchTerms: ['收集', 'collection'] },
      { type: 'HUMAN_INPUT', label: '人工输入', searchTerms: ['人工', 'human'] },
      { type: 'TRANSFER_TO_HUMAN', label: '转人工', searchTerms: ['handoff', '转接'] },
    ],
  },
  {
    title: '知识库',
    items: [
      { type: 'KNOWLEDGE', label: '知识库检索', searchTerms: ['知识', 'knowledge', 'rag'] },
    ],
  },
]

export function buildNodePaletteGroups(mode: NodePaletteMode): NodePaletteGroup[] {
  return COZE_NODE_PALETTE_GROUPS
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.modes || item.modes.includes(mode)),
    }))
    .filter((group) => group.items.length > 0)
}

export function filterNodePaletteGroups(groups: NodePaletteGroup[], keyword: string): NodePaletteGroup[] {
  const normalizedKeyword = keyword.trim().toLowerCase()
  if (!normalizedKeyword) return groups
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => `${item.label} ${(item.searchTerms || []).join(' ')}`.toLowerCase().includes(normalizedKeyword)),
    }))
    .filter((group) => group.items.length > 0)
}
