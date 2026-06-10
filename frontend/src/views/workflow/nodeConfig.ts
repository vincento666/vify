import type { WorkflowCanvasNode, WorkflowCanvasNodeType } from './flowGraph'

export type NodeConfigFieldType = 'text' | 'textarea' | 'number' | 'select' | 'readonly'
  | 'code-editor'
  | 'switch'
  | 'resource-select'
  | 'output-parameters'
  | 'aggregation-output-summary'
  | 'input-parameters'
  | 'condition-branches'
  | 'start-variables'
  | 'end-response'
  | 'end-answer-content'
  | 'question-options'
  | 'collection-fields'
  | 'intent-rows'
  | 'resource-adapter-badge'
  | 'schema-input-mappings'
  | 'legacy-resource-debug'
  | 'json-field-mappings'
  | 'aggregation-sources'
  | 'aggregation-groups'
  | 'variable-assignment'
  | 'human-input-schema'

export type OutputFormat = '文本' | 'Markdown' | 'JSON'
export type OutputParameterType = 'string' | 'number' | 'boolean' | 'object' | 'array'
export type InputParameterType = OutputParameterType
export type InputValueMode = 'reference' | 'literal'

export interface OutputParameter {
  name: string
  type: OutputParameterType
  valueMode?: InputValueMode
  value?: string | number | boolean
}

export interface InputParameter {
  name: string
  type: InputParameterType
  valueMode: InputValueMode
  value: string | number | boolean
}

export interface StartVariable {
  name: string
  type: InputParameterType
  required: boolean
  builtIn: boolean
}

export interface QuestionOption {
  label: string
  value: string
}

export interface CollectionField {
  name: string
  type: InputParameterType
  required: boolean
  description: string
  targetScope: string
  targetVariable: string
}

export interface IntentRow {
  key: string
  name: string
  description: string
  examples: string[]
  branch: string
}

export interface JsonFieldMapping {
  name: string
  path: string
  type: InputParameterType
}

export interface AggregationSource {
  name: string
  valueMode: InputValueMode
  value: string | number | boolean
}

export interface AggregationGroupVariable {
  valueMode: InputValueMode
  value: string | number | boolean
}

export interface AggregationGroup {
  name: string
  type: OutputParameterType
  variables: AggregationGroupVariable[]
}

export interface HumanInputSchemaField {
  name: string
  type: InputParameterType
  required: boolean
  description: string
}

export interface NormalizedOutputConfig {
  format: OutputFormat
  parameters: OutputParameter[]
}

export interface NormalizedInputConfig {
  parameters: InputParameter[]
}

export interface NodeConfigField {
  key: string
  label: string
  type: NodeConfigFieldType
  placeholder?: string
  options?: string[]
  resourceTypes?: string[]
  min?: number
  max?: number
  step?: number
}

export interface NodeConfigSection {
  title: string
  fields: NodeConfigField[]
}

export interface NodeConfigSchema {
  type: WorkflowCanvasNodeType
  title: string
  sections: NodeConfigSection[]
}

export const OUTPUT_FORMAT_OPTIONS: OutputFormat[] = ['文本', 'Markdown', 'JSON']
export const OUTPUT_PARAMETER_TYPE_OPTIONS: OutputParameterType[] = ['string', 'number', 'boolean', 'object', 'array']

const BUILT_IN_START_VARIABLE_NAMES = new Set([
  'USER_INPUT',
  'BOT_USER_INPUT',
  'CONVERSATION_NAME',
  'userMessage',
  'user_query',
  'userQuery',
  'input',
  'sys.query',
  'sys.conversation_id',
  'sys.conversation_name',
  'sys.user_id',
  'sys.channel',
  'sys.channel_id',
  'sys.now',
  'sys.message_id',
  'sys.round',
  'sys.files',
])

export function isBuiltInStartVariableName(name: string) {
  return BUILT_IN_START_VARIABLE_NAMES.has(String(name || '').trim())
}

const OUTPUT_SECTION: NodeConfigSection = {
  title: '输出',
  fields: [{ key: 'outputParameters', label: '输出参数', type: 'output-parameters' }],
}

const INPUT_SECTION: NodeConfigSection = {
  title: '输入',
  fields: [{ key: 'inputParameters', label: '输入', type: 'input-parameters' }],
}

const SCHEMAS: Record<WorkflowCanvasNodeType, NodeConfigSchema> = {
  START: {
    type: 'START',
    title: '开始',
    sections: [
      {
        title: '输入',
        fields: [{ key: 'startVariables', label: '输入', type: 'start-variables' }],
      },
    ],
  },
  LLM: {
    type: 'LLM',
    title: '大模型',
    sections: [
      INPUT_SECTION,
      {
        title: '系统提示词',
        fields: [{ key: 'systemPrompt', label: '系统提示词', type: 'textarea', placeholder: '输入系统提示词，可使用变量引用' }],
      },
      {
        title: '用户提示词',
        fields: [{ key: 'prompt', label: '用户提示词', type: 'textarea', placeholder: '输入用户提示词，可使用 {{variable}} 引用参数' }],
      },
      {
        title: '输出',
        fields: [
          { key: 'streamOutput', label: '流式输出', type: 'switch' },
          { key: 'outputParameters', label: '输出参数', type: 'output-parameters' },
        ],
      },
      {
        title: '技能调用',
        fields: [
          { key: 'toolChoiceMode', label: '工具选择', type: 'select', options: ['auto', 'required', 'disabled'] },
          { key: 'maxToolRounds', label: '最大调用轮次', type: 'number', min: 1, max: 3, step: 1, placeholder: '1' },
          { key: 'toolResultMode', label: '工具结果', type: 'select', options: ['append', 'separate'] },
        ],
      },
      {
        title: '模型参数',
        fields: [
          { key: 'temperature', label: '温度', type: 'number', min: 0, max: 2, step: 0.01, placeholder: '0.7' },
          { key: 'maxTokens', label: '最大输出 Token', type: 'number', min: 1, max: 200000, step: 1, placeholder: '2048' },
          { key: 'topP', label: 'Top P', type: 'number', min: 0, max: 1, step: 0.01, placeholder: '1' },
          { key: 'frequencyPenalty', label: '频率惩罚', type: 'number', min: -2, max: 2, step: 0.01, placeholder: '0' },
          { key: 'presencePenalty', label: '存在惩罚', type: 'number', min: -2, max: 2, step: 0.01, placeholder: '0' },
          { key: 'responseFormat', label: '响应格式', type: 'select', options: ['文本', 'JSON'] },
          { key: 'stopSequences', label: '停止词', type: 'textarea', placeholder: '每行一个停止词' },
          { key: 'seed', label: '随机种子', type: 'number', min: 0, max: 2147483647, step: 1, placeholder: '可选' },
        ],
      },
    ],
  },
  CONDITION: {
    type: 'CONDITION',
    title: '选择器',
    sections: [
      {
        title: '条件分支',
        fields: [{ key: 'conditionBranches', label: '条件分支', type: 'condition-branches' }],
      },
    ],
  },
  KNOWLEDGE: {
    type: 'KNOWLEDGE',
    title: '知识检索',
    sections: [
      INPUT_SECTION,
      {
        title: '知识库',
        fields: [
          { key: 'resourceId', label: '知识库', type: 'resource-select', resourceTypes: ['KNOWLEDGE_BASE'], placeholder: '选择知识库' },
          { key: 'query', label: '检索问题', type: 'textarea', placeholder: '{{start.USER_INPUT}}' },
          { key: 'retrievalMode', label: '检索方式', type: 'select', options: ['auto', 'hybrid', 'semantic', 'keyword', 'faq'] },
          { key: 'topK', label: '返回条数', type: 'number', placeholder: '5' },
          { key: 'scoreThreshold', label: '最低命中分', type: 'number', placeholder: '0' },
          { key: 'rerank', label: '结果重排', type: 'switch' },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  API_CALL: {
    type: 'API_CALL',
    title: 'API 调用',
    sections: [
      INPUT_SECTION,
      {
        title: 'API Resource',
        fields: [
          { key: 'resourceId', label: 'API Resource', type: 'resource-select', resourceTypes: ['API_TOOL', 'API_RESOURCE'], placeholder: '选择 API Resource 或 API Tool' },
        ],
      },
      {
        title: '参数映射',
        fields: [{ key: 'schemaInputMappings', label: '参数映射', type: 'schema-input-mappings' }],
      },
      {
        title: '请求',
        fields: [
          { key: 'endpoint', label: '请求地址', type: 'text', placeholder: 'https://api.example.com' },
          { key: 'method', label: '请求方法', type: 'select', options: ['GET', 'POST', 'PUT', 'DELETE'] },
          { key: 'headers', label: '请求头', type: 'textarea', placeholder: '[{\"name\":\"X-Token\",\"value\":\"{{sys.run_id}}\"}]' },
          { key: 'body', label: '请求体', type: 'textarea', placeholder: '{\"message\":\"{{start.USER_INPUT}}\"}' },
          { key: 'timeout', label: '超时秒数', type: 'number', min: 1, max: 120, step: 1, placeholder: '30' },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  TOOL_CALL: {
    type: 'TOOL_CALL',
    title: '工具调用',
    sections: [
      INPUT_SECTION,
      {
        title: '工具',
        fields: [
          { key: 'resourceId', label: '工具', type: 'resource-select', resourceTypes: ['MCP_TOOL', 'API_TOOL', 'INTERNAL_TOOL'], placeholder: '选择业务工具' },
          { key: 'adapterBadge', label: '适配器', type: 'resource-adapter-badge' },
        ],
      },
      {
        title: '参数映射',
        fields: [{ key: 'schemaInputMappings', label: '参数映射', type: 'schema-input-mappings' }],
      },
      {
        title: '错误处理',
        fields: [
          { key: 'retryCount', label: '重试次数', type: 'number', min: 0, max: 5, step: 1, placeholder: '0' },
          { key: 'errorBehavior', label: '错误行为', type: 'select', options: ['fail', 'continue', 'branch'] },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  EXECUTE_WORKFLOW: {
    type: 'EXECUTE_WORKFLOW',
    title: '工作流',
    sections: [
      INPUT_SECTION,
      {
        title: '工作流',
        fields: [
          { key: 'resourceId', label: '工作流', type: 'resource-select', resourceTypes: ['SUBWORKFLOW'], placeholder: '选择已发布工作流' },
        ],
      },
      {
        title: '参数映射',
        fields: [{ key: 'schemaInputMappings', label: '参数映射', type: 'schema-input-mappings' }],
      },
      OUTPUT_SECTION,
    ],
  },
  AGENT_CALL: {
    type: 'AGENT_CALL',
    title: '智能体',
    sections: [
      INPUT_SECTION,
      {
        title: '智能体',
        fields: [
          { key: 'resourceId', label: '智能体', type: 'resource-select', resourceTypes: ['AGENT'], placeholder: '选择智能体' },
        ],
      },
      {
        title: '输入与上下文',
        fields: [
          { key: 'messageTemplate', label: '消息模板', type: 'textarea', placeholder: '{{start.USER_INPUT}} 或 {{start.sys.query}}' },
          { key: 'schemaInputMappings', label: '参数映射', type: 'schema-input-mappings' },
          { key: 'historyMode', label: '会话历史', type: 'select', options: ['none', 'include', 'recent'] },
        ],
      },
      {
        title: '输出',
        fields: [
          { key: 'streamOutput', label: '流式输出', type: 'switch' },
          { key: 'outputParameters', label: '输出参数', type: 'output-parameters' },
        ],
      },
    ],
  },
  TRANSFER_TO_HUMAN: {
    type: 'TRANSFER_TO_HUMAN',
    title: '转人工',
    sections: [
      INPUT_SECTION,
      {
        title: '转接配置',
        fields: [
          { key: 'message', label: '转接提示', type: 'textarea', placeholder: '展示给用户的转人工提示' },
          { key: 'queue', label: '队列', type: 'text', placeholder: 'general / vip-support' },
          { key: 'reason', label: '转接原因', type: 'text', placeholder: 'user_request' },
          { key: 'priority', label: '优先级', type: 'select', options: ['low', 'normal', 'high', 'urgent'] },
          { key: 'slaMinutes', label: 'SLA 分钟', type: 'number', min: 1, max: 10080, step: 1, placeholder: '30' },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  CODE: {
    type: 'CODE',
    title: '代码',
    sections: [
      INPUT_SECTION,
      {
        title: '代码配置',
        fields: [
          { key: 'language', label: '语言', type: 'select', options: ['python', 'javascript'] },
          { key: 'code', label: '代码', type: 'code-editor', placeholder: "result = {'output': inputs.get('USER_INPUT', '')}" },
          { key: 'timeout', label: '超时秒数', type: 'number', min: 1, max: 60, step: 1, placeholder: '60' },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  TEXT_PROCESS: {
    type: 'TEXT_PROCESS',
    title: '文本处理',
    sections: [
      INPUT_SECTION,
      {
        title: '处理规则',
        fields: [
          { key: 'operation', label: '操作', type: 'select', options: ['format_template', 'concatenate', 'extract_regex', 'replace', 'trim'] },
          { key: 'template', label: '模板', type: 'textarea', placeholder: '可使用 {{start.USER_INPUT}} 引用变量' },
          { key: 'source', label: '源文本', type: 'textarea', placeholder: '用于提取、替换或裁剪的文本' },
          { key: 'pattern', label: '匹配表达式', type: 'text', placeholder: '正则表达式或查找内容' },
          { key: 'replacement', label: '替换为', type: 'text', placeholder: '替换文本' },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  JSON_PARSE: {
    type: 'JSON_PARSE',
    title: 'JSON 解析',
    sections: [
      INPUT_SECTION,
      {
        title: '解析配置',
        fields: [
          { key: 'source', label: 'JSON 来源', type: 'textarea', placeholder: '{{llm.answer}} 或 JSON 字符串' },
        ],
      },
      {
        title: '字段映射',
        fields: [{ key: 'jsonFieldMappings', label: '字段映射', type: 'json-field-mappings' }],
      },
      OUTPUT_SECTION,
    ],
  },
  VARIABLE_AGGREGATION: {
    type: 'VARIABLE_AGGREGATION',
    title: '变量聚合',
    sections: [
      {
        title: '聚合策略',
        fields: [
          { key: 'strategy', label: '聚合策略', type: 'select', options: ['first_non_empty'] },
        ],
      },
      {
        title: '变量分组',
        fields: [
          { key: 'aggregationGroups', label: '变量分组', type: 'aggregation-groups' },
        ],
      },
      {
        title: '输出',
        fields: [{ key: 'aggregationOutputs', label: '输出', type: 'aggregation-output-summary' }],
      },
    ],
  },
  VARIABLE_ASSIGN: {
    type: 'VARIABLE_ASSIGN',
    title: '变量赋值',
    sections: [
      {
        title: '输入',
        fields: [{ key: 'variableAssignment', label: '变量赋值', type: 'variable-assignment' }],
      },
    ],
  },
  INTENT_RECOGNITION: {
    type: 'INTENT_RECOGNITION',
    title: '意图识别',
    sections: [
      INPUT_SECTION,
      {
        title: '识别策略',
        fields: [
          { key: 'inputSource', label: '输入来源', type: 'textarea', placeholder: '{{start.sys.query}}' },
          { key: 'classifierMode', label: '分类模式', type: 'select', options: ['fake', 'llm'] },
          { key: 'includeHistory', label: '会话历史感知', type: 'switch' },
        ],
      },
      {
        title: '意图分支',
        fields: [{ key: 'intents', label: '意图行', type: 'intent-rows' }],
      },
      OUTPUT_SECTION,
    ],
  },
  MESSAGE: {
    type: 'MESSAGE',
    title: '消息',
    sections: [
      INPUT_SECTION,
      {
        title: '发送消息',
        fields: [
          { key: 'content', label: '发送内容', type: 'textarea', placeholder: '可使用变量引用' },
          { key: 'streamOutput', label: '流式输出', type: 'switch' },
          { key: 'streamTarget', label: '流式目标', type: 'select', options: ['message', 'debug-only'] },
          { key: 'fallbackMode', label: '失败回退', type: 'select', options: ['aggregate', 'fail'] },
        ],
      },
      OUTPUT_SECTION,
    ],
  },
  QUESTION: {
    type: 'QUESTION',
    title: '问题',
    sections: [
      INPUT_SECTION,
      {
        title: '提问并等待',
        fields: [
          { key: 'question', label: '问题内容', type: 'textarea', placeholder: '询问用户的问题' },
          { key: 'answerType', label: '答案类型', type: 'select', options: ['text', 'number', 'option', 'json'] },
          { key: 'resumeBehavior', label: '恢复行为', type: 'select', options: ['wait', 'timeout_continue', 'timeout_fail'] },
          { key: 'timeoutSeconds', label: '超时秒数', type: 'number', min: 0, max: 86400, step: 1 },
        ],
      },
      {
        title: '回答选项',
        fields: [{ key: 'options', label: '选项行', type: 'question-options' }],
      },
      OUTPUT_SECTION,
    ],
  },
  HUMAN_INPUT: {
    type: 'HUMAN_INPUT',
    title: '人工输入',
    sections: [
      INPUT_SECTION,
      {
        title: '人工处理',
        fields: [
          { key: 'prompt', label: '提示内容', type: 'textarea', placeholder: '给人工处理者的提示' },
          { key: 'approvalMode', label: '审批模式', type: 'select', options: ['input', 'approval'] },
          { key: 'assigneeRole', label: '处理角色', type: 'text', placeholder: '客服主管' },
        ],
      },
      {
        title: '输入结构',
        fields: [{ key: 'humanInputSchema', label: '输入结构', type: 'human-input-schema' }],
      },
      OUTPUT_SECTION,
    ],
  },
  INFORMATION_COLLECTION: {
    type: 'INFORMATION_COLLECTION',
    title: '信息收集',
    sections: [
      INPUT_SECTION,
      {
        title: '收集策略',
        fields: [
          { key: 'inputSource', label: '输入来源', type: 'textarea', placeholder: '{{start.sys.query}}' },
          { key: 'collectionKey', label: '状态键', type: 'text', placeholder: 'profile' },
          { key: 'includeHistory', label: '会话历史感知', type: 'switch' },
          { key: 'writeToConversation', label: '写入会话上下文', type: 'switch' },
          { key: 'extractorMode', label: '抽取模式', type: 'select', options: ['fake', 'llm'] },
          { key: 'maxRounds', label: '最大收集轮次', type: 'number', min: 1, max: 20, step: 1 },
          { key: 'streamOutput', label: '追问流式输出', type: 'switch' },
        ],
      },
      {
        title: '收集字段',
        fields: [{ key: 'fields', label: '字段行', type: 'collection-fields' }],
      },
      OUTPUT_SECTION,
    ],
  },
  END: {
    type: 'END',
    title: '结束',
    sections: [
      {
        title: '输出',
        fields: [{ key: 'outputParameters', label: '输出参数', type: 'output-parameters' }],
      },
      {
        title: '回答内容',
        fields: [{ key: 'answerContent', label: '回答内容', type: 'end-answer-content' }],
      },
    ],
  },
}

export function getNodeConfigSchema(type: WorkflowCanvasNodeType): NodeConfigSchema {
  return SCHEMAS[type]
}

export function compactVariableTypeLabel(type: OutputParameterType | 'file'): string {
  return {
    string: 'str.',
    number: 'num.',
    boolean: 'bool.',
    object: 'obj.',
    array: 'arr.',
    file: 'file.',
  }[type]
}

function normalizeOutputFormat(value: unknown): OutputFormat {
  return OUTPUT_FORMAT_OPTIONS.includes(value as OutputFormat) ? value as OutputFormat : '文本'
}

function normalizeOutputType(value: unknown): OutputParameterType {
  return OUTPUT_PARAMETER_TYPE_OPTIONS.includes(value as OutputParameterType) ? value as OutputParameterType : 'string'
}

function parseArrayValue(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  if (typeof value !== 'string') return []
  const trimmed = value.trim()
  if (!trimmed) return []
  try {
    const parsed = JSON.parse(trimmed)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function normalizeInputValue(value: unknown, type: InputParameterType, mode: InputValueMode): string | number | boolean {
  if (mode === 'reference') return String(value || '')
  if (type === 'number') {
    const numberValue = Number(value)
    return Number.isFinite(numberValue) ? numberValue : 0
  }
  if (type === 'boolean') return value === true || value === 'true'
  if (type === 'object' || type === 'array') {
    if (typeof value === 'string') return value
    return JSON.stringify(value ?? (type === 'array' ? [] : {}))
  }
  return String(value ?? '')
}

export function normalizeStartVariables(config: Record<string, any> = {}): StartVariable[] {
  const declaredVariables = Array.isArray(config.startVariables)
    ? config.startVariables
      .map((item) => {
        const name = String(item?.name || '').trim()
        const builtIn = item?.builtIn === true || isBuiltInStartVariableName(name)
        return {
          name,
          type: normalizeOutputType(item?.type),
          required: builtIn ? false : item?.required !== false,
          builtIn,
        }
      })
      .filter((item) => item.name.length > 0)
    : []

  if (declaredVariables.length > 0) return declaredVariables

  const legacyVariables = Array.isArray(config.outputVariables)
    ? config.outputVariables.map((item) => String(item || '').trim()).filter((item) => item.length > 0)
    : ['USER_INPUT']

  return legacyVariables.map((name) => {
    const builtIn = isBuiltInStartVariableName(name)
    return { name, type: 'string', required: !builtIn, builtIn }
  })
}

export function normalizeQuestionOptions(config: Record<string, any> = {}): QuestionOption[] {
  return parseArrayValue(config.options)
    .map((item) => {
      if (typeof item === 'string') {
        const value = item.trim()
        return { label: value, value }
      }
      return {
        label: String((item as any)?.label ?? (item as any)?.name ?? (item as any)?.value ?? '').trim(),
        value: String((item as any)?.value ?? (item as any)?.label ?? (item as any)?.name ?? '').trim(),
      }
    })
    .filter((item) => item.label.length > 0 || item.value.length > 0)
}

export function normalizeCollectionFields(config: Record<string, any> = {}): CollectionField[] {
  return parseArrayValue(config.fields)
    .map((item) => {
      const rawType = (item as any)?.type ?? (item as any)?.fieldType
      const name = String((item as any)?.name ?? (item as any)?.key ?? '').trim()
      return {
        name,
        type: normalizeOutputType(rawType),
        required: (item as any)?.required !== false,
        description: String((item as any)?.description ?? '').trim(),
        targetScope: String((item as any)?.targetScope ?? 'flow').trim() || 'flow',
        targetVariable: String((item as any)?.targetVariable ?? name).trim(),
      }
    })
    .filter((item) => item.name.length > 0)
}

export function normalizeIntentRows(config: Record<string, any> = {}): IntentRow[] {
  return parseArrayValue(config.intents)
    .map((item) => {
      const examples = Array.isArray((item as any)?.examples)
        ? (item as any).examples.map((example: unknown) => String(example || '').trim()).filter((example: string) => example.length > 0)
        : String((item as any)?.examples || '')
          .split('\n')
          .map((example) => example.trim())
          .filter((example) => example.length > 0)
      const key = String((item as any)?.key ?? (item as any)?.id ?? '').trim()
      return {
        key,
        name: String((item as any)?.name ?? key).trim(),
        description: String((item as any)?.description ?? '').trim(),
        examples,
        branch: String((item as any)?.branch ?? (item as any)?.branchKey ?? key).trim(),
      }
    })
    .filter((item) => item.key.length > 0)
}

export function normalizeJsonFieldMappings(config: Record<string, any> = {}): JsonFieldMapping[] {
  return parseArrayValue(config.fieldMap ?? config.mappings)
    .map((item) => {
      const name = String((item as any)?.name ?? (item as any)?.key ?? '').trim()
      return {
        name,
        path: String((item as any)?.path ?? (item as any)?.jsonPath ?? (item as any)?.sourcePath ?? '').trim(),
        type: normalizeOutputType((item as any)?.type),
      }
    })
    .filter((item) => item.name.length > 0 && item.path.length > 0)
}

function inferInputValueMode(value: unknown, explicitMode: unknown): InputValueMode {
  if (explicitMode === 'literal') return 'literal'
  const text = String(value ?? '').trim()
  if (explicitMode === 'reference') return text ? 'reference' : 'literal'
  return text.includes('{{') ? 'reference' : 'literal'
}

export function normalizeAggregationSources(config: Record<string, any> = {}): AggregationSource[] {
  return parseArrayValue(config.sources ?? config.inputSources)
    .map((item) => {
      const value = (item as any)?.value ?? ''
      const valueMode = inferInputValueMode(value, (item as any)?.valueMode)
      return {
        name: String((item as any)?.name ?? (item as any)?.label ?? '').trim(),
        valueMode,
        value: normalizeInputValue(value, 'string', valueMode),
      }
    })
    .filter((item) => item.name.length > 0)
}

export function normalizeAggregationGroups(config: Record<string, any> = {}): AggregationGroup[] {
  const nestedGroups = (config as any)?.inputs?.mergeGroups
  const rawGroups = parseArrayValue(config.groups ?? config.mergeGroups ?? nestedGroups)
  const groups = rawGroups
    .map((group, groupIndex) => {
      const name = String((group as any)?.name ?? (group as any)?.groupName ?? `Group${groupIndex + 1}`).trim()
      const type = normalizeOutputType((group as any)?.type ?? (group as any)?.variableType)
      const variables = parseArrayValue((group as any)?.variables ?? (group as any)?.values)
        .map((item) => {
          const value = typeof item === 'string' ? item : (item as any)?.value ?? ''
          const valueMode = inferInputValueMode(value, typeof item === 'string' ? undefined : (item as any)?.valueMode)
          const isEmptyLiteral = valueMode !== 'reference' && String(value ?? '').trim() === ''
          return {
            valueMode,
            value: isEmptyLiteral ? '' : normalizeInputValue(value, type, valueMode),
          }
        })
      return {
        name,
        type,
        variables: withTrailingAggregationCandidate(variables.length > 0 ? variables : []),
      }
    })
    .filter((group) => group.name.length > 0)
  if (groups.length > 0) return groups

  const legacySources = normalizeAggregationSources(config)
  const output = normalizeOutputConfig(config).parameters[0]
  return [
    {
      name: output?.name || String(config.outputVariable || 'Group1'),
      type: output?.type || 'string',
      variables: withTrailingAggregationCandidate(legacySources.length > 0
        ? legacySources.map((source) => ({ valueMode: source.valueMode, value: source.value }))
        : []),
    },
  ]
}

function withTrailingAggregationCandidate(variables: AggregationGroupVariable[]): AggregationGroupVariable[] {
  const nonTrailingEmpty = variables.filter((item, index) => {
    const isEmptyLiteral = item.valueMode !== 'reference' && String(item.value ?? '').trim() === ''
    return !isEmptyLiteral || index < variables.length - 1
  })
  const last = nonTrailingEmpty[nonTrailingEmpty.length - 1]
  if (!last || last.valueMode === 'reference' || String(last.value ?? '').trim() !== '') {
    return [...nonTrailingEmpty, { valueMode: 'literal', value: '' }]
  }
  return nonTrailingEmpty
}

export function normalizeHumanInputSchema(config: Record<string, any> = {}): HumanInputSchemaField[] {
  return parseArrayValue(config.inputSchema ?? config.schema)
    .map((item) => {
      const name = String((item as any)?.name ?? (item as any)?.key ?? '').trim()
      return {
        name,
        type: normalizeOutputType((item as any)?.type ?? (item as any)?.fieldType),
        required: (item as any)?.required !== false,
        description: String((item as any)?.description ?? '').trim(),
      }
    })
    .filter((item) => item.name.length > 0)
}

export function normalizeInputConfig(config: Record<string, any> = {}): NormalizedInputConfig {
  const parameters = Array.isArray(config.inputParameters)
    ? config.inputParameters
      .map((item) => {
        const type = normalizeOutputType(item?.type)
        const valueMode = inferInputValueMode(item?.value, item?.valueMode)
        return {
          name: String(item?.name || '').trim(),
          type,
          valueMode,
          value: normalizeInputValue(item?.value, type, valueMode),
        }
      })
      .filter((item) => item.name.length > 0)
    : []

  return { parameters }
}

export function normalizeOutputConfig(
  config: Record<string, any> = {},
  options: { respectExplicitEmpty?: boolean } = {},
): NormalizedOutputConfig {
  const hasExplicitOutputParameters = Array.isArray(config.outputParameters)
  const declaredParameters = Array.isArray(config.outputParameters)
    ? config.outputParameters
      .map((item) => {
        const type = normalizeOutputType(item?.type)
        const parameter: OutputParameter = {
          name: String(item?.name || '').trim(),
          type,
        }
        const hasValueConfig = Object.prototype.hasOwnProperty.call(item || {}, 'value')
          || Object.prototype.hasOwnProperty.call(item || {}, 'valueMode')
        if (hasValueConfig) {
          const valueMode = item?.valueMode === 'reference'
            ? 'reference'
            : inferInputValueMode(item?.value, item?.valueMode)
          parameter.valueMode = valueMode
          parameter.value = normalizeInputValue(item?.value, type, valueMode)
        }
        return parameter
      })
      .filter((item) => item.name.length > 0)
    : []

  if (declaredParameters.length > 0) {
    return {
      format: normalizeOutputFormat(config.outputFormat),
      parameters: declaredParameters,
    }
  }
  if (hasExplicitOutputParameters && options.respectExplicitEmpty) {
    return {
      format: normalizeOutputFormat(config.outputFormat),
      parameters: [],
    }
  }

  const legacyName = String(config.outputVariable || 'output').trim() || 'output'
  return {
    format: normalizeOutputFormat(config.outputFormat),
    parameters: [{ name: legacyName, type: 'string' }],
  }
}

export function validateOutputParameters(parameters: OutputParameter[]): string[] {
  const errors: string[] = []
  const seen = new Set<string>()
  for (const parameter of parameters) {
    const name = parameter.name.trim()
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
      errors.push(`输出变量 ${name || '未命名'} 只能包含字母、数字和下划线，且不能以数字开头`)
      continue
    }
    if (seen.has(name)) {
      errors.push(`输出变量 ${name} 重复`)
      continue
    }
    seen.add(name)
  }
  return errors
}

export function validateInputParameters(parameters: InputParameter[]): string[] {
  const errors: string[] = []
  const seen = new Set<string>()
  for (const parameter of parameters) {
    const name = parameter.name.trim()
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
      errors.push(`输入变量 ${name || '未命名'} 只能包含字母、数字和下划线，且不能以数字开头`)
      continue
    }
    if (seen.has(name)) {
      errors.push(`输入变量 ${name} 重复`)
      continue
    }
    seen.add(name)
    if (parameter.valueMode === 'reference' && !String(parameter.value || '').trim()) {
      errors.push(`输入变量 ${name} 需要选择引用变量`)
    }
  }
  return errors
}

export function applyNodeConfigPatch(
  node: WorkflowCanvasNode,
  patch: { name?: string; config?: Record<string, any> },
): WorkflowCanvasNode {
  return {
    ...node,
    name: patch.name ?? node.name,
    config: {
      ...node.config,
      ...(patch.config || {}),
      ui: node.config.ui,
    },
  }
}
