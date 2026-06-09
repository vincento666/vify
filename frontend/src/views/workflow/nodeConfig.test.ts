import { describe, expect, it } from 'vitest'

import {
  applyNodeConfigPatch,
  compactVariableTypeLabel,
  getNodeConfigSchema,
  normalizeInputConfig,
  normalizeOutputConfig,
  normalizeStartVariables,
  validateInputParameters,
  normalizeCollectionFields,
  normalizeAggregationGroups,
  normalizeAggregationSources,
  normalizeHumanInputSchema,
  normalizeIntentRows,
  normalizeJsonFieldMappings,
  normalizeQuestionOptions,
  validateOutputParameters,
} from './nodeConfig'

describe('workflow node config schema', () => {
  it('does not expose node-name editing fields on any node panel', () => {
    for (const type of ['START', 'LLM', 'CONDITION', 'KNOWLEDGE', 'API_CALL', 'CODE', 'TEXT_PROCESS', 'JSON_PARSE', 'VARIABLE_AGGREGATION', 'VARIABLE_ASSIGN', 'INTENT_RECOGNITION', 'MESSAGE', 'QUESTION', 'HUMAN_INPUT', 'INFORMATION_COLLECTION', 'TOOL_CALL', 'EXECUTE_WORKFLOW', 'AGENT_CALL', 'TRANSFER_TO_HUMAN', 'END'] as const) {
      expect(getNodeConfigSchema(type).sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain('name')
    }
  })

  it('uses switch controls for stream-output fields instead of select rows', () => {
    const messageStream = getNodeConfigSchema('MESSAGE')
      .sections.flatMap((section) => section.fields)
      .find((field) => field.key === 'streamOutput')
    const collectionStream = getNodeConfigSchema('INFORMATION_COLLECTION')
      .sections.flatMap((section) => section.fields)
      .find((field) => field.key === 'streamOutput')

    expect(messageStream?.type).toBe('switch')
    expect(collectionStream?.type).toBe('switch')
  })

  it('uses registry-backed selector for TOOL_CALL resources', () => {
    const resourceField = getNodeConfigSchema('TOOL_CALL')
      .sections.flatMap((section) => section.fields)
      .find((field) => field.key === 'resourceId')

    expect(resourceField?.type).toBe('resource-select')
  })

  it('uses compact variable type labels in selectors and parameter rows', () => {
    expect(compactVariableTypeLabel('string')).toBe('str.')
    expect(compactVariableTypeLabel('number')).toBe('num.')
    expect(compactVariableTypeLabel('boolean')).toBe('bool.')
    expect(compactVariableTypeLabel('object')).toBe('obj.')
    expect(compactVariableTypeLabel('array')).toBe('arr.')
    expect(compactVariableTypeLabel('file')).toBe('file.')
  })

  it('provides runtime-backed editable fields for each canvas node type', () => {
    expect(getNodeConfigSchema('START').sections.map((section) => section.title)).toEqual(['输入'])
    expect(getNodeConfigSchema('START').sections.flatMap((section) => section.fields.map((field) => field.type))).toEqual([
      'start-variables',
    ])
    expect(getNodeConfigSchema('LLM').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining([
        'inputParameters',
        'systemPrompt',
        'prompt',
        'temperature',
        'maxTokens',
        'topP',
        'frequencyPenalty',
        'presencePenalty',
        'responseFormat',
        'stopSequences',
        'seed',
        'toolChoiceMode',
        'maxToolRounds',
        'toolResultMode',
        'outputParameters',
      ]),
    )
    expect(getNodeConfigSchema('CONDITION').sections.map((section) => section.title)).toEqual(['条件分支'])
    expect(getNodeConfigSchema('CONDITION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual([
      'conditionBranches',
    ])
    expect(getNodeConfigSchema('KNOWLEDGE').title).toBe('知识检索')
    expect(getNodeConfigSchema('KNOWLEDGE').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['resourceId', 'query', 'retrievalMode', 'topK', 'scoreThreshold', 'rerank', 'outputParameters']),
    )
    expect(getNodeConfigSchema('API_CALL').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['endpoint', 'method', 'headers', 'body', 'timeout', 'outputParameters']),
    )
    expect(getNodeConfigSchema('CODE').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['language', 'code', 'timeout', 'outputParameters']),
    )
    expect(getNodeConfigSchema('TEXT_PROCESS').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['operation', 'template', 'pattern', 'replacement', 'outputParameters']),
    )
    expect(getNodeConfigSchema('JSON_PARSE').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['source', 'jsonFieldMappings', 'outputParameters']),
    )
    expect(getNodeConfigSchema('VARIABLE_AGGREGATION').sections.map((section) => section.title)).toEqual([
      '聚合策略',
      '变量分组',
      '输出',
    ])
    expect(getNodeConfigSchema('VARIABLE_AGGREGATION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['strategy', 'aggregationGroups', 'aggregationOutputs']),
    )
    expect(getNodeConfigSchema('VARIABLE_AGGREGATION').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toEqual(
      expect.arrayContaining(['inputParameters', 'sources', 'defaultValue', 'separator']),
    )
    expect(getNodeConfigSchema('VARIABLE_ASSIGN').sections.map((section) => section.title)).toEqual(['输入'])
    expect(getNodeConfigSchema('VARIABLE_ASSIGN').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['variableAssignment']),
    )
    expect(getNodeConfigSchema('VARIABLE_ASSIGN').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain(
      'outputParameters',
    )
    expect(getNodeConfigSchema('VARIABLE_ASSIGN').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toEqual(
      expect.arrayContaining(['targetScope', 'targetVariable', 'writeMode']),
    )
    expect(getNodeConfigSchema('INTENT_RECOGNITION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['inputSource', 'intents', 'classifierMode', 'includeHistory', 'outputParameters']),
    )
    expect(getNodeConfigSchema('INTENT_RECOGNITION').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain(
      'defaultIntent',
    )
    expect(getNodeConfigSchema('MESSAGE').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['content', 'streamOutput', 'streamTarget', 'fallbackMode', 'outputParameters']),
    )
    expect(getNodeConfigSchema('QUESTION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['question', 'answerType', 'options', 'timeoutSeconds', 'outputParameters']),
    )
    expect(getNodeConfigSchema('HUMAN_INPUT').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['prompt', 'humanInputSchema', 'approvalMode', 'assigneeRole', 'outputParameters']),
    )
    expect(getNodeConfigSchema('INFORMATION_COLLECTION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['inputSource', 'fields', 'collectionKey', 'includeHistory', 'maxRounds', 'streamOutput', 'outputParameters']),
    )
    expect(getNodeConfigSchema('TOOL_CALL').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['resourceId', 'adapterBadge', 'schemaInputMappings', 'retryCount', 'errorBehavior', 'outputParameters']),
    )
    expect(getNodeConfigSchema('EXECUTE_WORKFLOW').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['resourceId', 'schemaInputMappings', 'outputParameters']),
    )
    expect(getNodeConfigSchema('AGENT_CALL').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['resourceId', 'schemaInputMappings', 'messageTemplate', 'historyMode', 'outputParameters']),
    )
    expect(getNodeConfigSchema('TRANSFER_TO_HUMAN').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['message', 'queue', 'reason', 'priority', 'slaMinutes', 'outputParameters']),
    )
    expect(getNodeConfigSchema('END').sections.map((section) => section.title)).toEqual(['输出', '回答内容'])
    expect(getNodeConfigSchema('END').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain(
      'inputParameters',
    )
    expect(getNodeConfigSchema('END').sections.flatMap((section) => section.fields.map((field) => field.type))).not.toContain(
      'end-response',
    )
  })

  it('models END output variables as a normal output section and keeps return mode panel-level', () => {
    const fields = getNodeConfigSchema('END').sections.flatMap((section) => section.fields)

    expect(fields).toEqual([
      { key: 'outputParameters', label: '输出参数', type: 'output-parameters' },
      { key: 'answerContent', label: '回答内容', type: 'end-answer-content' },
    ])
  })

  it('puts LLM core sections in Coze-like order before advanced settings', () => {
    const sections = getNodeConfigSchema('LLM').sections

    expect(sections.map((section) => section.title).slice(0, 4)).toEqual([
      '输入',
      '系统提示词',
      '用户提示词',
      '输出',
    ])
    expect(sections.find((section) => section.title === '系统提示词')?.fields).toEqual([
      { key: 'systemPrompt', label: '系统提示词', type: 'textarea', placeholder: '输入系统提示词，可使用变量引用' },
    ])
    expect(sections.find((section) => section.title === '用户提示词')?.fields).toEqual([
      { key: 'prompt', label: '用户提示词', type: 'textarea', placeholder: '输入用户提示词，可使用 {{variable}} 引用参数' },
    ])
  })

  it('uses structured Coze-like editors for secondary Chatflow panels', () => {
    const messageFields = getNodeConfigSchema('MESSAGE').sections.flatMap((section) => section.fields)
    expect(getNodeConfigSchema('MESSAGE').sections.map((section) => section.title)).toEqual([
      '输入',
      '发送消息',
      '输出',
    ])
    expect(messageFields.find((field) => field.key === 'content')).toMatchObject({
      label: '发送内容',
      type: 'textarea',
    })
    expect(messageFields.find((field) => field.key === 'streamOutput')).toMatchObject({
      label: '流式输出',
      type: 'switch',
    })

    const questionFields = getNodeConfigSchema('QUESTION').sections.flatMap((section) => section.fields)
    expect(getNodeConfigSchema('QUESTION').sections.map((section) => section.title)).toEqual([
      '输入',
      '提问并等待',
      '回答选项',
      '输出',
    ])
    expect(questionFields.find((field) => field.key === 'options')).toMatchObject({
      label: '选项行',
      type: 'question-options',
    })
    expect(questionFields.find((field) => field.key === 'options')?.type).not.toBe('textarea')

    const collectionFields = getNodeConfigSchema('INFORMATION_COLLECTION').sections.flatMap((section) => section.fields)
    expect(getNodeConfigSchema('INFORMATION_COLLECTION').sections.map((section) => section.title)).toEqual([
      '输入',
      '收集策略',
      '收集字段',
      '输出',
    ])
    expect(collectionFields.find((field) => field.key === 'fields')).toMatchObject({
      label: '字段行',
      type: 'collection-fields',
    })
    expect(collectionFields.find((field) => field.key === 'writeToConversation')).toMatchObject({
      label: '写入会话上下文',
      type: 'switch',
    })

    const intentFields = getNodeConfigSchema('INTENT_RECOGNITION').sections.flatMap((section) => section.fields)
    expect(getNodeConfigSchema('INTENT_RECOGNITION').sections.map((section) => section.title)).toEqual([
      '输入',
      '识别策略',
      '意图分支',
      '输出',
    ])
    expect(intentFields.find((field) => field.key === 'intents')).toMatchObject({
      label: '意图行',
      type: 'intent-rows',
    })
    expect(intentFields.find((field) => field.key === 'intents')?.type).not.toBe('textarea')
  })

  it('normalizes secondary Chatflow row editors without raw JSON strings', () => {
    expect(normalizeQuestionOptions({ options: '["是", {"label":"否","value":"no"}]' })).toEqual([
      { label: '是', value: '是' },
      { label: '否', value: 'no' },
    ])

    expect(normalizeCollectionFields({
      fields: [
        { name: 'phone', type: 'string', required: true, description: '手机号', targetScope: 'conversation', targetVariable: 'customer_phone' },
        { name: '', type: 'unknown', required: false },
      ],
    })).toEqual([
      { name: 'phone', type: 'string', required: true, description: '手机号', targetScope: 'conversation', targetVariable: 'customer_phone' },
    ])

    expect(normalizeIntentRows({
      intents: [
        { key: 'refund', name: '退款', description: '退款咨询', examples: ['我要退款', '退货'], branch: 'refund_branch' },
        { key: '', name: '空', examples: [] },
      ],
    })).toEqual([
      { key: 'refund', name: '退款', description: '退款咨询', examples: ['我要退款', '退货'], branch: 'refund_branch' },
    ])
  })

  it('keeps resource-node raw ids and JSON mappings out of basic panels', () => {
    const toolCall = getNodeConfigSchema('TOOL_CALL')
    const toolBasicFields = toolCall.sections
      .filter((section) => section.title !== '高级/兼容配置')
      .flatMap((section) => section.fields)
    expect(toolCall.sections.map((section) => section.title)).toEqual([
      '输入',
      '工具',
      '参数映射',
      '错误处理',
      '输出',
    ])
    expect(toolBasicFields.map((field) => field.key)).toEqual(
      expect.arrayContaining(['resourceId', 'adapterBadge', 'schemaInputMappings', 'retryCount', 'errorBehavior', 'outputParameters']),
    )
    expect(toolBasicFields.map((field) => field.type)).toEqual(
      expect.arrayContaining(['resource-select', 'resource-adapter-badge', 'schema-input-mappings']),
    )
    expect(toolBasicFields.map((field) => field.key)).not.toEqual(
      expect.arrayContaining(['serverIds', 'toolName', 'inputMappings']),
    )

    for (const type of ['KNOWLEDGE', 'EXECUTE_WORKFLOW', 'AGENT_CALL'] as const) {
      const basicFields = getNodeConfigSchema(type).sections
        .filter((section) => section.title !== '高级/兼容配置')
        .flatMap((section) => section.fields)
      expect(basicFields.map((field) => field.type)).toContain('resource-select')
      expect(basicFields.map((field) => field.key)).not.toEqual(
        expect.arrayContaining(['knowledgeBaseId', 'targetWorkflowId', 'targetAgentId', 'inputMappings', 'outputMappings']),
      )
    }

    const apiCall = getNodeConfigSchema('API_CALL')
    expect(apiCall.sections.find((section) => section.title === 'API Resource')?.fields.map((field) => field.type)).toContain(
      'resource-select',
    )
    expect(apiCall.sections.find((section) => section.title === '参数映射')?.fields.map((field) => field.type)).toContain(
      'schema-input-mappings',
    )
  })

  it('does not expose advanced compatibility sections in node config panels', () => {
    const nodeTypes = [
      'START',
      'END',
      'LLM',
      'CONDITION',
      'KNOWLEDGE',
      'API_CALL',
      'TOOL_CALL',
      'EXECUTE_WORKFLOW',
      'AGENT_CALL',
      'CODE',
      'TEXT_PROCESS',
      'JSON_PARSE',
      'VARIABLE_AGGREGATION',
      'VARIABLE_ASSIGN',
      'HUMAN_INPUT',
      'INFORMATION_COLLECTION',
      'INTENT_RECOGNITION',
      'MESSAGE',
      'QUESTION',
      'TRANSFER_TO_HUMAN',
    ] as const

    for (const type of nodeTypes) {
      expect(getNodeConfigSchema(type).sections.map((section) => section.title)).not.toContain('高级/兼容配置')
    }
  })

  it('hides legacy resource technical fields from node panels', () => {
    for (const type of ['TOOL_CALL', 'KNOWLEDGE', 'EXECUTE_WORKFLOW', 'AGENT_CALL'] as const) {
      const fields = getNodeConfigSchema(type).sections.flatMap((section) => section.fields)
      expect(fields.map((field) => field.key)).not.toContain('legacyResourceDebug')
      expect(fields.map((field) => field.type)).not.toContain('legacy-resource-debug')
    }
  })

  it('uses structured editors for data and structured nodes instead of raw JSON in basic panels', () => {
    const expectations = [
      { type: 'JSON_PARSE', structuredType: 'json-field-mappings', rawKeys: ['fieldMap'], advancedRawKeys: [] },
      { type: 'VARIABLE_AGGREGATION', structuredType: 'aggregation-groups', rawKeys: ['groups', 'sources'], advancedRawKeys: [] },
      { type: 'VARIABLE_ASSIGN', structuredType: 'variable-assignment', rawKeys: ['targetScope', 'targetVariable', 'source', 'writeMode'], advancedRawKeys: [] },
      { type: 'HUMAN_INPUT', structuredType: 'human-input-schema', rawKeys: ['inputSchema'], advancedRawKeys: [] },
    ] as const

    for (const expectation of expectations) {
      const schema = getNodeConfigSchema(expectation.type)
      const basicFields = schema.sections
        .filter((section) => section.title !== '高级/兼容配置')
        .flatMap((section) => section.fields)
      const advancedFields = schema.sections
        .filter((section) => section.title === '高级/兼容配置')
        .flatMap((section) => section.fields)

      expect(basicFields.map((field) => field.type)).toContain(expectation.structuredType)
      expect(basicFields.map((field) => field.key)).not.toEqual(expect.arrayContaining([...expectation.rawKeys]))
      if (expectation.advancedRawKeys.length > 0) {
        expect(advancedFields.map((field) => field.key)).toEqual(expect.arrayContaining([...expectation.advancedRawKeys]))
      } else {
        expect(advancedFields.map((field) => field.key)).toEqual([])
      }
    }
  })

  it('normalizes structured data node rows from legacy JSON-compatible config', () => {
    expect(normalizeJsonFieldMappings({
      fieldMap: '[{"name":"order_id","path":"$.order.id","type":"number"},{"name":"","path":"$.skip"}]',
    })).toEqual([
      { name: 'order_id', path: '$.order.id', type: 'number' },
    ])

    expect(normalizeAggregationSources({
      sources: [
        { name: 'primary', value: '{{start.primary}}' },
        { name: 'fallback', value: 'vip' },
      ],
    })).toEqual([
      { name: 'primary', valueMode: 'reference', value: '{{start.primary}}' },
      { name: 'fallback', valueMode: 'literal', value: 'vip' },
    ])

    expect(normalizeAggregationGroups({
      groups: [
        {
          name: 'Group1',
          type: 'string',
          variables: [{ value: '{{start.primary}}' }, { value: 'vip' }],
        },
      ],
    })).toEqual([
      {
        name: 'Group1',
        type: 'string',
        variables: [
          { valueMode: 'reference', value: '{{start.primary}}' },
          { valueMode: 'literal', value: 'vip' },
          { valueMode: 'literal', value: '' },
        ],
      },
    ])

    expect(normalizeAggregationGroups({
      outputVariable: 'selected',
      sources: [
        { name: 'primary', value: '{{start.primary}}' },
        { name: 'fallback', value: 'vip' },
      ],
    })[0]).toEqual({
      name: 'selected',
      type: 'string',
      variables: [
        { valueMode: 'reference', value: '{{start.primary}}' },
        { valueMode: 'literal', value: 'vip' },
        { valueMode: 'literal', value: '' },
      ],
    })

    expect(normalizeHumanInputSchema({
      inputSchema: '[{"name":"approved","type":"boolean","required":true,"description":"是否通过"}]',
    })).toEqual([
      { name: 'approved', type: 'boolean', required: true, description: '是否通过' },
    ])
  })

  it('normalizes START variables into Coze-like input rows while preserving legacy outputVariables', () => {
    expect(normalizeStartVariables({ outputVariables: ['USER_INPUT', 'ticket_id'] })).toEqual([
      { name: 'USER_INPUT', type: 'string', required: false, builtIn: true },
      { name: 'ticket_id', type: 'string', required: true, builtIn: false },
    ])

    expect(normalizeStartVariables({
      outputVariables: ['legacy'],
      startVariables: [
        { name: 'sys.query', type: 'string', required: true },
        { name: 'age', type: 'number', required: false },
      ],
    })).toEqual([
      { name: 'sys.query', type: 'string', required: false, builtIn: true },
      { name: 'age', type: 'number', required: false, builtIn: false },
    ])
  })

  it('adds a shared input parameter editor field to runnable middle node schemas', () => {
    for (const type of ['LLM', 'KNOWLEDGE', 'API_CALL', 'CODE', 'TEXT_PROCESS', 'JSON_PARSE', 'INTENT_RECOGNITION', 'MESSAGE', 'QUESTION', 'HUMAN_INPUT', 'INFORMATION_COLLECTION', 'TOOL_CALL', 'EXECUTE_WORKFLOW', 'AGENT_CALL', 'TRANSFER_TO_HUMAN'] as const) {
      expect(getNodeConfigSchema(type).sections.flatMap((section) => section.fields.map((field) => field.key))).toContain(
        'inputParameters',
      )
    }
    expect(getNodeConfigSchema('VARIABLE_AGGREGATION').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain(
      'inputParameters',
    )
    expect(getNodeConfigSchema('VARIABLE_ASSIGN').sections.flatMap((section) => section.fields.map((field) => field.key))).not.toContain(
      'inputParameters',
    )
  })

  it('updates node name and config without dropping ui position metadata', () => {
    const updated = applyNodeConfigPatch(
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        position: { x: 320, y: 240 },
        config: { ui: { position: { x: 320, y: 240 } }, outputVariable: 'output' },
      },
      {
        name: '意图识别',
        config: { prompt: '识别用户意图', outputVariable: 'intent' },
      },
    )

    expect(updated.name).toBe('意图识别')
    expect(updated.config).toMatchObject({
      prompt: '识别用户意图',
      outputVariable: 'intent',
      ui: { position: { x: 320, y: 240 } },
    })
  })

  it('normalizes Coze-like output format and output parameter rows', () => {
    const config = normalizeOutputConfig({
      outputFormat: 'Markdown',
      outputParameters: [
        { name: 'answer', type: 'string' },
        { name: 'reasoning', type: 'object' },
      ],
    })

    expect(config.format).toBe('Markdown')
    expect(config.parameters).toEqual([
      { name: 'answer', type: 'string' },
      { name: 'reasoning', type: 'object' },
    ])
  })

  it('keeps END-style output variable mappings for upstream references', () => {
    const config = normalizeOutputConfig({
      outputFormat: 'JSON',
      outputParameters: [
        { name: 'final', type: 'string', valueMode: 'reference', value: '{{llm_1.answer}}' },
      ],
    })

    expect(config).toEqual({
      format: 'JSON',
      parameters: [
        { name: 'final', type: 'string', valueMode: 'reference', value: '{{llm_1.answer}}' },
      ],
    })
  })

  it('keeps legacy outputVariable compatible while validating duplicate and illegal names', () => {
    const legacy = normalizeOutputConfig({ outputVariable: 'answer' })

    expect(legacy).toEqual({
      format: '文本',
      parameters: [{ name: 'answer', type: 'string' }],
    })
    expect(validateOutputParameters([
      { name: 'answer', type: 'string' },
      { name: 'answer', type: 'number' },
      { name: 'bad-name', type: 'string' },
    ])).toEqual([
      '输出变量 answer 重复',
      '输出变量 bad-name 只能包含字母、数字和下划线，且不能以数字开头',
    ])
  })

  it('normalizes and validates typed input parameter rows', () => {
    const input = normalizeInputConfig({
      inputParameters: [
        { name: 'question', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' },
        { name: 'limit', type: 'number', valueMode: 'literal', value: '3' },
        { name: '', type: 'unknown', valueMode: 'bad', value: '' },
      ],
    })

    expect(input.parameters).toEqual([
      { name: 'question', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' },
      { name: 'limit', type: 'number', valueMode: 'literal', value: 3 },
    ])
    expect(validateInputParameters([
      { name: 'question', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' },
      { name: 'question', type: 'number', valueMode: 'literal', value: 1 },
      { name: 'bad-name', type: 'string', valueMode: 'literal', value: '' },
      { name: 'missing_ref', type: 'string', valueMode: 'reference', value: '' },
    ])).toEqual([
      '输入变量 question 重复',
      '输入变量 bad-name 只能包含字母、数字和下划线，且不能以数字开头',
      '输入变量 missing_ref 需要选择引用变量',
    ])
  })
})
