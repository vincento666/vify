import { describe, expect, it } from 'vitest'

import {
  agentDetailToForm,
  defaultAgentWorkbenchForm,
  formToAgentCreatePayload,
  formToAgentUpdatePayload,
  buildPreviewWelcomeState,
  buildPreviewTargetOptions,
  buildPreviewVariableOverrides,
  summarizeAgentCapabilities,
  resolveAgentRuntimeMode,
  resolveFlowCanvasPath,
  resolvePreviewGate,
  buildWorkbenchReadinessMessages,
  formatWorkbenchBackendError,
  groupModelOptions,
  isAgentFormDirty,
  validateAgentWorkbenchForm,
} from './agentWorkbench'
import type { AgentDetail, ModelOption } from '@/api/agent'
import type { AgentVersionList } from '@/api/agent'

describe('agent workbench form helpers', () => {
  it('maps Agent detail to a stable editable form and preserves API payload compatibility', () => {
    const detail: AgentDetail = {
      id: 7,
      name: 'Refund Agent',
      description: 'handles refunds',
      systemPrompt: 'Answer with policy.',
      modelConfigId: 42,
      temperature: 0.2,
      maxTokens: 512,
      maxContextTurns: 6,
      openingMessage: '你好，我是退款助手。',
      suggestedQuestions: ['如何退款？', '多久到账？'],
      enabled: 1,
      toolIds: [3, 4],
      knowledgeBaseId: 11,
      knowledgeBaseIds: [11, 12],
      retrievalSettings: { topK: 4, scoreThreshold: 0.5, retrievalMode: 'keyword', rerank: true, citationStyle: 'numbered' },
      evaluationGate: { enabled: true, experimentId: 9, requiredPassRate: 0.8 },
      access: { mode: 'PRIVATE', owners: ['vincento'], readonly: false },
      sharing: { enabled: true, publicToken: 'pub-test' },
      catalog: { visible: true, category: 'support' },
      analytics: { usage: 3, latencyMs: 120, errors: 0 },
      workflowId: null,
      createdAt: '2026-06-02T00:00:00',
      updatedAt: '2026-06-02T00:00:00',
      variables: [
        { name: 'customer_name', type: 'string', defaultValue: 'Ada', required: true, description: 'customer' },
      ],
      memory: { profile: 'concise' },
      toolPolicies: {
        lookup_order: { enabled: true, callMode: 'auto', argumentPresets: {}, timeoutMs: 30000 },
      },
    }

    const form = agentDetailToForm(detail)

    expect(form).toEqual({
      name: 'Refund Agent',
      description: 'handles refunds',
      systemPrompt: 'Answer with policy.',
      modelConfigId: 42,
      temperature: 0.2,
      maxTokens: 512,
      maxContextTurns: 6,
      openingMessage: '你好，我是退款助手。',
      suggestedQuestions: ['如何退款？', '多久到账？'],
      toolIds: [3, 4],
      knowledgeBaseId: 11,
      knowledgeBaseIds: [11, 12],
      retrievalSettings: { topK: 4, scoreThreshold: 0.5, retrievalMode: 'keyword', rerank: true, citationStyle: 'numbered' },
      evaluationGate: { enabled: true, experimentId: 9, requiredPassRate: 0.8 },
      access: { mode: 'PRIVATE', owners: ['vincento'], readonly: false },
      sharing: { enabled: true, publicToken: 'pub-test' },
      catalog: { visible: true, category: 'support' },
      analytics: { usage: 3, latencyMs: 120, errors: 0 },
      workflowId: null,
      variables: [
        { name: 'customer_name', type: 'string', defaultValue: 'Ada', required: true, description: 'customer' },
      ],
      memory: { profile: 'concise' },
      toolPolicies: {
        lookup_order: {
          enabled: true,
          callMode: 'auto',
          argumentPresets: {},
          approvalRequired: false,
          timeoutMs: 30000,
          failureBehavior: 'return_error',
        },
      },
    })
    expect(formToAgentCreatePayload(form)).toEqual({
      name: 'Refund Agent',
      description: 'handles refunds',
      systemPrompt: 'Answer with policy.',
      modelConfigId: 42,
      temperature: 0.2,
      maxTokens: 512,
      maxContextTurns: 6,
      openingMessage: '你好，我是退款助手。',
      suggestedQuestions: ['如何退款？', '多久到账？'],
      toolIds: [3, 4],
      knowledgeBaseId: 11,
      knowledgeBaseIds: [11, 12],
      retrievalSettings: { topK: 4, scoreThreshold: 0.5, retrievalMode: 'keyword', rerank: true, citationStyle: 'numbered' },
      evaluationGate: { enabled: true, experimentId: 9, requiredPassRate: 0.8 },
      access: { mode: 'PRIVATE', owners: ['vincento'], readonly: false },
      sharing: { enabled: true, publicToken: 'pub-test' },
      catalog: { visible: true, category: 'support' },
      analytics: { usage: 3, latencyMs: 120, errors: 0 },
      workflowId: null,
      variables: [
        { name: 'customer_name', type: 'string', defaultValue: 'Ada', required: true, description: 'customer' },
      ],
      memory: { profile: 'concise' },
      toolPolicies: {
        lookup_order: {
          enabled: true,
          callMode: 'auto',
          argumentPresets: {},
          approvalRequired: false,
          timeoutMs: 30000,
          failureBehavior: 'return_error',
        },
      },
    })
    expect(formToAgentUpdatePayload(form)).toEqual({
      name: 'Refund Agent',
      description: 'handles refunds',
      systemPrompt: 'Answer with policy.',
      modelConfigId: 42,
      temperature: 0.2,
      maxTokens: 512,
      maxContextTurns: 6,
      openingMessage: '你好，我是退款助手。',
      suggestedQuestions: ['如何退款？', '多久到账？'],
      knowledgeBaseId: 11,
      knowledgeBaseIds: [11, 12],
      retrievalSettings: { topK: 4, scoreThreshold: 0.5, retrievalMode: 'keyword', rerank: true, citationStyle: 'numbered' },
      evaluationGate: { enabled: true, experimentId: 9, requiredPassRate: 0.8 },
      access: { mode: 'PRIVATE', owners: ['vincento'], readonly: false },
      sharing: { enabled: true, publicToken: 'pub-test' },
      catalog: { visible: true, category: 'support' },
      analytics: { usage: 3, latencyMs: 120, errors: 0 },
      workflowId: null,
      variables: [
        { name: 'customer_name', type: 'string', defaultValue: 'Ada', required: true, description: 'customer' },
      ],
      memory: { profile: 'concise' },
      toolPolicies: {
        lookup_order: {
          enabled: true,
          callMode: 'auto',
          argumentPresets: {},
          approvalRequired: false,
          timeoutMs: 30000,
          failureBehavior: 'return_error',
        },
      },
    })
  })

  it('validates required core fields and detects dirty state', () => {
    const baseline = defaultAgentWorkbenchForm()
    const invalid = validateAgentWorkbenchForm(baseline)

    expect(invalid).toEqual(expect.arrayContaining([
      expect.objectContaining({ field: 'name' }),
      expect.objectContaining({ field: 'modelConfigId' }),
    ]))

    const current = { ...baseline, name: 'Support Agent', modelConfigId: 9 }

    expect(validateAgentWorkbenchForm(current)).toEqual([])
    expect(isAgentFormDirty(current, baseline)).toBe(true)
    expect(isAgentFormDirty(baseline, defaultAgentWorkbenchForm())).toBe(false)
  })

  it('groups model options by provider for the workbench selector', () => {
    const options: ModelOption[] = [
      { modelConfigId: 1, modelName: 'mimo', providerName: 'OpenRouter', providerType: 'OPENAI' },
      { modelConfigId: 2, modelName: 'gpt', providerName: 'OpenRouter', providerType: 'OPENAI' },
      { modelConfigId: 3, modelName: 'claude', providerName: 'Anthropic', providerType: 'ANTHROPIC' },
    ]

    expect(groupModelOptions(options)).toEqual([
      { providerName: 'OpenRouter', models: [options[0], options[1]] },
      { providerName: 'Anthropic', models: [options[2]] },
    ])
  })

  it('summarizes capability bindings for cards and persistence', () => {
    const form = {
      ...defaultAgentWorkbenchForm(),
      toolIds: [8, 9],
      knowledgeBaseId: 12,
      workflowId: 13,
    }

    expect(summarizeAgentCapabilities(form)).toEqual({
      toolCount: 2,
      hasKnowledgeBase: true,
      hasWorkflow: true,
      summary: '2 个 MCP Server / 知识库 / 工作流',
    })
  })

  it('resolves runtime mode and precedence warnings like backend chat behavior', () => {
    expect(resolveAgentRuntimeMode({
      ...defaultAgentWorkbenchForm(),
      toolIds: [1],
      knowledgeBaseId: 2,
      workflowId: 3,
    })).toEqual({
      mode: 'workflow',
      badge: '工作流',
      summary: '工作流优先运行并决定回复路径',
      warnings: [
        '已绑定知识库，但工作流优先，RAG 不会直接参与本次 Agent 聊天路径。',
        '已绑定 MCP 工具，但工作流模式优先，工具不会进入模型工具调用路径。',
      ],
    })

    expect(resolveAgentRuntimeMode({
      ...defaultAgentWorkbenchForm(),
      toolIds: [1],
      knowledgeBaseId: 2,
    })).toEqual({
      mode: 'rag',
      badge: 'RAG',
      summary: '知识库会在模型回答前被检索',
      warnings: ['已绑定 MCP 工具，但 RAG 模式优先，工具不会进入模型工具调用路径。'],
    })

    expect(resolveAgentRuntimeMode({
      ...defaultAgentWorkbenchForm(),
      toolIds: [1],
    }).mode).toBe('direct-tools')
  })

  it('requires saved clean Agent state before preview can send', () => {
    expect(resolvePreviewGate({ isCreateMode: true, dirty: false, streaming: false })).toEqual({
      canSend: false,
      reason: '请先保存 Agent 后再预览。',
    })
    expect(resolvePreviewGate({ isCreateMode: false, dirty: true, streaming: false })).toEqual({
      canSend: false,
      reason: '当前配置有未保存更改，请保存后再预览。',
    })
    expect(resolvePreviewGate({ isCreateMode: false, dirty: false, streaming: true })).toEqual({
      canSend: false,
      reason: '正在生成回复。',
    })
    expect(resolvePreviewGate({ isCreateMode: false, dirty: false, streaming: false })).toEqual({
      canSend: true,
      reason: '',
    })
  })

  it('builds dependency empty states and backend error text for readiness polish', () => {
    expect(buildWorkbenchReadinessMessages({
      modelCount: 0,
      mcpServerCount: 0,
      knowledgeBaseCount: 0,
      workflowCount: 0,
    })).toEqual([
      '暂无可用模型，请先在模型提供商中启用模型。',
      '暂无启用的 MCP Server，可先到 MCP 管理中添加。',
      '暂无启用知识库，可先创建知识库。',
      '暂无工作流，可先创建 Workflow。',
    ])

    expect(formatWorkbenchBackendError({ message: 'MCP server not available: 99' })).toBe('MCP server not available: 99')
    expect(formatWorkbenchBackendError(new Error('Network down'))).toBe('Network down')
    expect(formatWorkbenchBackendError(null)).toBe('保存 Agent 失败')
  })

  it('builds preview welcome state from opening message and suggested questions', () => {
    const form = {
      ...defaultAgentWorkbenchForm(),
      openingMessage: ' 你好，我能帮你处理售后问题。 ',
      suggestedQuestions: [' 如何退款？ ', '', '查订单状态', '如何退款？'],
    }

    expect(buildPreviewWelcomeState(form)).toEqual({
      openingMessage: '你好，我能帮你处理售后问题。',
      suggestedQuestions: ['如何退款？', '查订单状态'],
    })
  })

  it('builds draft latest and released preview target options from Agent versions', () => {
    const versions: AgentVersionList = {
      latestVersionId: 11,
      releasedVersionId: 10,
      list: [
        {
          id: 11,
          agentId: 7,
          versionNo: 2,
          name: 'candidate',
          snapshot: { name: 'Agent v2' },
          released: false,
          releasedAt: null,
          createdAt: '2026-06-02T00:00:00',
          updatedAt: '2026-06-02T00:00:00',
        },
        {
          id: 10,
          agentId: 7,
          versionNo: 1,
          name: 'release',
          snapshot: { name: 'Agent v1' },
          released: true,
          releasedAt: '2026-06-02T00:01:00',
          createdAt: '2026-06-02T00:00:00',
          updatedAt: '2026-06-02T00:01:00',
        },
      ],
    }

    expect(buildPreviewTargetOptions(versions)).toEqual([
      { value: 'draft', label: 'Draft 当前草稿', description: '使用当前已保存 Agent 配置' },
      { value: 'latest:11', label: 'Latest v2 candidate', description: '最近保存的不可变版本' },
      { value: 'released:10', label: 'Released v1 release', description: '当前发布版本' },
    ])
  })

  it('builds preview variable overrides from non-empty form values only', () => {
    expect(buildPreviewVariableOverrides({
      customer_name: ' Vincent ',
      tier: '',
      order_count: 3,
    })).toEqual({
      customer_name: 'Vincent',
      order_count: 3,
    })
  })

  it('resolves workflow and chatflow canvas paths from flow type', () => {
    expect(resolveFlowCanvasPath({ id: 1, flowType: 'WORKFLOW' })).toBe('/workflows/1/canvas')
    expect(resolveFlowCanvasPath({ id: 2, flowType: 'CHATFLOW' })).toBe('/chatflows/2/canvas')
  })
})
