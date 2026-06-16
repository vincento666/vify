import type {
  RuntimeLabChatflowTrace,
  RuntimeLabConfig,
  RuntimeLabRouteDecision,
  RuntimeLabTask,
  RuntimeLabTraceNode,
  RuntimeLabTurn,
  RuntimeLabUsage,
  RuntimeLabTemporaryModelPayload,
} from '@/api/runtimeLab'

export interface AirlineSopScenario {
  id: string
  label: string
  shortLabel: string
  triggerUtterances: string[]
  sampleReplies: string[]
}

export interface RuntimeLabTranscriptRow {
  id: string
  role: 'user' | 'assistant'
  content: string
  pending?: boolean
  elapsedMs?: number
  usage?: RuntimeLabUsage
  debugDetail?: RuntimeLabDebugDetail
  routeAction?: string
  targetSopId?: string | null
  taskSummary?: string
  resumePrompt?: string
}

export interface RuntimeLabDebugStep {
  id: string
  label: string
  elapsedMs: number
  input: unknown
  output: unknown
  usage: RuntimeLabUsage
}

export interface RuntimeLabDebugDetail {
  title: string
  subtitle: string
  elapsedMs: number
  input: unknown
  output: unknown
  usage: RuntimeLabUsage
  steps: RuntimeLabDebugStep[]
}

export interface RuntimeLabConfigSummary {
  bindingLabel: string
  arbitratorLabel: string
  fallbackAgentLabel: string
  secretLabel: string
  availableLabel: string
  bindingRows: string[]
}

export interface RuntimeLabLocalSettings {
  arbitratorMode: string
  arbitratorModelConfigId: number | null
  arbitratorModel: string
  fallbackModelConfigId: number | null
  fallbackModel: string
  baseUrl: string
  temporaryModel: RuntimeLabTemporaryModelSettings
  temporaryFallbackModel: RuntimeLabTemporaryModelSettings
  apiKeyConfigured: boolean
  arbitratorAvailable: boolean
  fallbackAgentEnabled: boolean
  fallbackAgentType: string
  fallbackAgentId: number | null
  strongAcceptThreshold: number
  classifierMinConfidence: number
  candidateTopK: number
  llmArbitrationRequiredForNonHardStop: boolean
  faqKeywordMinScore: number
  faqKeywordMinMargin: number
  faqSemanticMinScore: number
  faqSemanticMinMargin: number
  ragMinScore: number
  ragLexicalAcceptThreshold: number
  faqExactEnabled: boolean
  faqSemanticEnabled: boolean
  faqTopK: number
  faqRerank: boolean
  faqKnowledgeBaseIds: number[]
  ragEnabled: boolean
  ragRetrievalMode: string
  ragTopK: number
  ragRerank: boolean
  ragKnowledgeBaseIds: number[]
  handoffEnabled: boolean
  handoffQueue: string
}

export interface RuntimeLabTemporaryModelSettings {
  enabled: boolean
  model: string
  baseUrl: string
  apiKey: string
  temperature: number
  maxTokens: number
  topP: number
}

export interface RuntimeLabFunnelSummary {
  stageLabel: string
  sourceLabel: string
  arbitratorLabel: string
}

export interface RuntimeLabRouteOutcome {
  tone: 'neutral' | 'success' | 'warning' | 'danger'
  title: string
  detail: string
}

export interface RuntimeLabBoundScenarioRow {
  id: string
  label: string
  shortLabel: string
  triggerUtterances: string[]
  sampleReplies: string[]
  chatflowId: number
  chatflowName: string
  exists: boolean
  canvasPath: string
}

export interface RuntimeLabTraceCard {
  taskId: number
  sopId: string
  status: string
  chatflowName: string
  currentNodeLabel: string
  completedCountLabel: string
  canvasPath: string
  debugPath: string
  nodes: RuntimeLabTraceNode[]
  events: Array<{ id: number; type: string; nodeKey: string }>
  slotRows: Array<{ key: string; value: unknown }>
}

export const RUNTIME_LAB_MIN_PENDING_MS = 520

export const AIRLINE_SOP_SCENARIOS: AirlineSopScenario[] = [
  {
    id: 'flight_booking',
    label: '机票预订',
    shortLabel: '订票',
    triggerUtterances: [
      '我想买一张明天去上海的机票，时间最好别太早',
      '帮我订机票，两个人从北京飞成都，预算想控制一下',
      '临时出行需要订机票，麻烦帮我进入购票流程',
    ],
    sampleReplies: ['手机号 13800138000，乘机人张测试', '确认', '继续机票预订'],
  },
  {
    id: 'fare_quote',
    label: '票价咨询',
    shortLabel: '票价',
    triggerUtterances: [
      '我先不出票，想问下北京到上海今天票价大概多少',
      '帮我查一下机票报价，周五晚上飞深圳',
      '现在去成都的航班价格怎么样？我想比较一下',
    ],
    sampleReplies: ['订单号 CA0134，手机号 13800138000，乘机人张测试', '确认', '继续票价咨询'],
  },
  {
    id: 'group_booking',
    label: '团队订票',
    shortLabel: '团队',
    triggerUtterances: [
      '我们公司十六个人出差，想咨询团队机票怎么订',
      '帮我开团队订票流程，人数比较多需要统一出票',
      '团队机票能不能给报价？大概二十个人',
    ],
    sampleReplies: ['订单号 CA0234，手机号 13800138000，乘机人张测试', '确认', '继续团队订票'],
  },
  {
    id: 'ancillary_sales',
    label: '增值服务',
    shortLabel: '增值',
    triggerUtterances: [
      '买完票以后还能加购餐食和贵宾厅吗？',
      '我想给这张票加买保险和接送机服务',
      '帮我看看附加服务，行李和餐食一起买',
    ],
    sampleReplies: ['订单号 CA0334，手机号 13800138000，乘机人张测试', '确认', '继续增值服务'],
  },
  {
    id: 'refund_ticket',
    label: '退票办理',
    shortLabel: '退票',
    triggerUtterances: [
      '您好，我临时出差取消了，想把今晚这张机票退掉',
      '我不飞了，票款能不能退回来？',
      '昨天订错了航班，我要退票，但想先知道扣费',
    ],
    sampleReplies: ['订单号 CA1034，手机号 13800138000，乘机人张测试', '确认', '继续退票'],
  },
  {
    id: 'change_flight',
    label: '改签办理',
    shortLabel: '改签',
    triggerUtterances: [
      '我明天会议提前，想把航班改签到更早一班',
      '这趟来不及赶到机场，帮我换个航班',
      '计划变了，想调整航班时间，不知道差价多少',
    ],
    sampleReplies: ['订单号 CA2034，手机号 13800138000，乘机人张测试', '确认', '继续改签'],
  },
  {
    id: 'passenger_info_change',
    label: '资料修改',
    shortLabel: '资料',
    triggerUtterances: [
      '我证件号填错了一位，想修改乘机人信息',
      '订票时手机号写错了，能帮我改联系人吗？',
      '乘机人姓名拼音有问题，需要更正一下',
    ],
    sampleReplies: ['订单号 CA2134，手机号 13800138000，乘机人张测试', '确认', '继续资料修改'],
  },
  {
    id: 'invoice_apply',
    label: '发票申请',
    shortLabel: '发票',
    triggerUtterances: [
      '公司报销要凭证，帮我开一下电子发票',
      '我需要行程单和发票，抬头稍后给你',
      '上周飞完了，现在需要报销凭证',
    ],
    sampleReplies: ['订单号 CA3034，手机号 13800138000，乘机人张测试', '确认', '继续发票申请'],
  },
  {
    id: 'baggage_service',
    label: '行李服务',
    shortLabel: '行李',
    triggerUtterances: [
      '我带了两个箱子，想加购托运行李额',
      '行李可能超重，帮我看看能不能提前买',
      '我有婴儿车和箱子，问下行李怎么处理',
    ],
    sampleReplies: ['订单号 CA4034，手机号 13800138000，乘机人张测试', '确认', '继续行李服务'],
  },
  {
    id: 'seat_checkin',
    label: '值机选座',
    shortLabel: '选座',
    triggerUtterances: [
      '我想线上值机，最好选靠窗座位',
      '帮我选座，同行两个人想坐一起',
      '能不能帮我办登机牌？订单稍后发',
    ],
    sampleReplies: ['订单号 CA5034，手机号 13800138000，乘机人张测试', '确认', '继续值机选座'],
  },
  {
    id: 'flight_status',
    label: '航班动态',
    shortLabel: '动态',
    triggerUtterances: [
      '我想查一下今天航班动态，听说天气不好',
      '帮我看航班是不是延误了，机场通知不清楚',
      '查一下到达时间，司机在等',
    ],
    sampleReplies: ['航班号 CA6034，今天北京飞广州', '确认', '继续航班动态'],
  },
  {
    id: 'special_assistance',
    label: '特殊协助',
    shortLabel: '协助',
    triggerUtterances: [
      '老人第一次坐飞机，需要轮椅协助',
      '我腿受伤了，想申请特殊旅客服务',
      '我要申请特殊服务，航班信息稍后发',
    ],
    sampleReplies: ['订单号 CA2234，手机号 13800138000，乘机人张测试', '确认', '继续特殊协助'],
  },
  {
    id: 'pet_cabin',
    label: '宠物乘机',
    shortLabel: '宠物',
    triggerUtterances: [
      '我想带猫坐飞机，问下宠物进客舱要求',
      '我要办理宠物托运，小狗证件都有',
      '宠物能不能随身带？需要什么材料',
    ],
    sampleReplies: ['订单号 CA3234，手机号 13800138000，乘机人张测试', '确认', '继续宠物乘机'],
  },
  {
    id: 'irregular_flight',
    label: '异常航班',
    shortLabel: '异常',
    triggerUtterances: [
      '航班取消了，我需要改签或补偿方案',
      '延误四小时，客服说可以非自愿处理',
      '我遇到不正常航班，想知道能不能改到明天',
    ],
    sampleReplies: ['订单号 CA4234，手机号 13800138000，乘机人张测试', '确认', '继续异常航班'],
  },
  {
    id: 'membership_service',
    label: '会员里程',
    shortLabel: '会员',
    triggerUtterances: [
      '我的会员里程没到账，帮我补登一下',
      '常旅客账号积分不对，想查明细',
      '帮我补登里程，登机牌还在',
    ],
    sampleReplies: ['订单号 CA5234，手机号 13800138000，乘机人张测试', '确认', '继续会员里程'],
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

export function buildRuntimeLabTranscriptRow(turn: RuntimeLabTurn, elapsedMs = 0): RuntimeLabTranscriptRow {
  const debugDetail = buildRouteDebugDetail(turn, elapsedMs)
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: turn.reply,
    elapsedMs,
    usage: debugDetail.usage,
    debugDetail,
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

export function buildRuntimeLabConfigSummary(config: RuntimeLabConfig | null): RuntimeLabConfigSummary {
  if (!config) {
    return {
      bindingLabel: '配置加载中',
      arbitratorLabel: '-',
      fallbackAgentLabel: '-',
      secretLabel: '-',
      availableLabel: '-',
      bindingRows: [],
    }
  }
  const mode = config.arbitrator.mode || 'fake'
  const model = config.arbitrator.model || '-'
  const fallbackModel = config.arbitrator.fallbackModel || ''
  const fallbackAgent = config.fallbackAgent
  const fallbackAgentLabel = fallbackAgent?.enabled
    ? `${fallbackAgent.type || 'fake'} · ${fallbackAgent.agentName || fallbackAgent.agentId || '未绑定'}`
    : '未启用'
  return {
    bindingLabel: `已绑定 ${config.sopBindings.length} 个 Chatflow SOP`,
    arbitratorLabel: fallbackModel ? `${mode} · ${model} / fallback ${fallbackModel}` : `${mode} · ${model}`,
    fallbackAgentLabel,
    secretLabel: config.arbitrator.apiKeyConfigured ? 'API Key 已配置' : 'API Key 未配置',
    availableLabel: config.arbitrator.available ? '可用' : '不可用',
    bindingRows: config.sopBindings.map((binding) => {
      const name = binding.chatflowName || '未找到 Chatflow'
      const status = binding.exists ? 'ok' : 'missing'
      return `${binding.sopId} -> #${binding.chatflowId} ${name} (${status})`
    }),
  }
}

export function buildRuntimeLabLocalSettings(config: RuntimeLabConfig | null): RuntimeLabLocalSettings {
  const thresholds = config?.thresholds || {}
  const faq = config?.faq || { knowledgeBaseIds: [] }
  const rag = config?.rag || { knowledgeBaseIds: [] }
  const fallbackAgent = config?.fallbackAgent
  return {
    arbitratorMode: config?.arbitrator.mode || 'fake',
    arbitratorModelConfigId: null,
    arbitratorModel: config?.arbitrator.model || '',
    fallbackModelConfigId: null,
    fallbackModel: config?.arbitrator.fallbackModel || '',
    baseUrl: config?.arbitrator.baseUrl || '',
    temporaryModel: defaultTemporaryModelSettings({
      model: config?.arbitrator.model || '',
      baseUrl: config?.arbitrator.baseUrl || '',
    }),
    temporaryFallbackModel: defaultTemporaryModelSettings({
      model: config?.arbitrator.fallbackModel || '',
      baseUrl: config?.arbitrator.baseUrl || '',
    }),
    apiKeyConfigured: config?.arbitrator.apiKeyConfigured === true,
    arbitratorAvailable: config?.arbitrator.available === true,
    fallbackAgentEnabled: fallbackAgent?.enabled === true,
    fallbackAgentType: fallbackAgent?.type || 'fake',
    fallbackAgentId: fallbackAgent?.agentId ?? null,
    strongAcceptThreshold: finiteNumber(thresholds.strongAcceptThreshold, 0.9),
    classifierMinConfidence: finiteNumber(thresholds.classifierMinConfidence, 0.6),
    candidateTopK: Math.max(1, Math.round(finiteNumber(thresholds.candidateTopK, 5))),
    llmArbitrationRequiredForNonHardStop: thresholds.llmArbitrationRequiredForNonHardStop !== false,
    faqKeywordMinScore: finiteNumber(thresholds.faqKeywordMinScore, 0.72),
    faqKeywordMinMargin: finiteNumber(thresholds.faqKeywordMinMargin, 0.08),
    faqSemanticMinScore: finiteNumber(thresholds.faqSemanticMinScore, 0.72),
    faqSemanticMinMargin: finiteNumber(thresholds.faqSemanticMinMargin, 0.08),
    ragMinScore: finiteNumber(thresholds.ragMinScore, 0.72),
    ragLexicalAcceptThreshold: finiteNumber(thresholds.ragLexicalAcceptThreshold, 0.42),
    faqExactEnabled: faq.exactEnabled !== false,
    faqSemanticEnabled: faq.semanticEnabled !== false,
    faqTopK: Math.max(1, Math.round(finiteNumber(faq.topK, 3))),
    faqRerank: faq.rerank === true,
    faqKnowledgeBaseIds: Array.isArray(faq.knowledgeBaseIds) ? [...faq.knowledgeBaseIds] : [],
    ragEnabled: rag.enabled !== false,
    ragRetrievalMode: rag.retrievalMode || 'hybrid',
    ragTopK: Math.max(1, Math.round(finiteNumber(rag.topK, 5))),
    ragRerank: rag.rerank === true,
    ragKnowledgeBaseIds: Array.isArray(rag.knowledgeBaseIds) ? [...rag.knowledgeBaseIds] : [],
    handoffEnabled: config?.handoff?.enabled !== false,
    handoffQueue: config?.handoff?.queue || 'general',
  }
}

export function defaultTemporaryModelSettings(
  seed: Partial<RuntimeLabTemporaryModelSettings> = {},
): RuntimeLabTemporaryModelSettings {
  return {
    enabled: seed.enabled ?? false,
    model: seed.model ?? '',
    baseUrl: seed.baseUrl ?? '',
    apiKey: seed.apiKey ?? '',
    temperature: finiteNumber(seed.temperature, 0),
    maxTokens: Math.max(1, Math.round(finiteNumber(seed.maxTokens, 360))),
    topP: finiteNumber(seed.topP, 1),
  }
}

export function buildRuntimeLabRouteSettingsPayload(settings: RuntimeLabLocalSettings) {
  const temporaryModel = temporaryModelPayload(settings.temporaryModel)
  const temporaryFallbackModel = temporaryModelPayload(settings.temporaryFallbackModel)
  return {
    arbitrator: {
      mode: settings.arbitratorMode,
      model: temporaryModel?.model || settings.arbitratorModel,
      fallbackModel: temporaryFallbackModel?.model || settings.fallbackModel,
      modelConfigId: temporaryModel ? null : settings.arbitratorModelConfigId,
      fallbackModelConfigId: temporaryFallbackModel ? null : settings.fallbackModelConfigId,
      ...(temporaryModel ? { temporaryModel } : {}),
      ...(temporaryFallbackModel ? { temporaryFallbackModel } : {}),
    },
    thresholds: {
      strongAcceptThreshold: settings.strongAcceptThreshold,
      classifierMinConfidence: settings.classifierMinConfidence,
      candidateTopK: settings.candidateTopK,
    },
  }
}

function temporaryModelPayload(settings: RuntimeLabTemporaryModelSettings): RuntimeLabTemporaryModelPayload | null {
  if (!settings.enabled) return null
  return {
    enabled: true,
    model: settings.model.trim(),
    baseUrl: settings.baseUrl.trim(),
    apiKey: settings.apiKey,
    temperature: settings.temperature,
    maxTokens: Math.max(1, Math.round(settings.maxTokens)),
    topP: settings.topP,
  }
}

export function buildRuntimeLabBoundScenarios(config: RuntimeLabConfig | null): RuntimeLabBoundScenarioRow[] {
  if (!config) return []
  return config.sopBindings.map((binding) => {
    const scenario = getAirlineSopScenario(binding.sopId)
    const canvasPath = stringValue(binding.canvasPath) || `/chatflows/${binding.chatflowId}/canvas`
    const fallbackLabel = binding.chatflowName || binding.sopId
    return {
      id: binding.sopId,
      label: scenario?.label || fallbackLabel,
      shortLabel: scenario?.shortLabel || fallbackLabel.slice(0, 4),
      triggerUtterances: scenario?.triggerUtterances || [],
      sampleReplies: scenario?.sampleReplies || [],
      chatflowId: binding.chatflowId,
      chatflowName: binding.chatflowName,
      exists: binding.exists,
      canvasPath,
    }
  })
}

export function buildRuntimeLabTraceCards(input: RuntimeLabChatflowTrace | null | undefined): RuntimeLabTraceCard[] {
  return (input?.tasks || []).map((task) => {
    const nodes = Array.isArray(task.nodes) ? task.nodes : []
    const currentNode = nodes.find((node) => node.current) || nodes.find((node) => isRunningNode(node.status)) || nodes[nodes.length - 1] || null
    const completed = nodes.filter((node) => isCompletedNode(node.status)).length
    const variables = task.variables || { businessRefs: {}, collected: {}, scoped: {}, session: {} }
    const businessRefs = variables.businessRefs || {}
    const collected = variables.collected || {}
    const slotSource = Object.keys(businessRefs).length ? businessRefs : collected
    return {
      taskId: Number(task.taskId || 0),
      sopId: task.sopId || '',
      status: task.status || '',
      chatflowName: task.chatflow?.chatflowName || '',
      currentNodeLabel: currentNode ? `${String(currentNode.nodeKey || '')} · ${String(currentNode.name || currentNode.nodeType || '')}` : '-',
      completedCountLabel: `${completed}/${nodes.length} 完成`,
      canvasPath: task.chatflow?.canvasPath || '',
      debugPath: task.chatflow?.debugPath || '',
      nodes,
      events: (task.events || []).map((event) => ({
        id: event.id,
        type: event.type,
        nodeKey: event.nodeKey,
      })),
      slotRows: Object.entries(slotSource).map(([key, value]) => ({ key, value: displayValue(value) })),
    }
  })
}

export function buildRuntimeLabNodeDebugDetail(
  card: RuntimeLabTraceCard,
  node: RuntimeLabTraceNode,
): RuntimeLabDebugDetail {
  const usage = normalizeUsage(node.usage || (node.outputs?.__usage as Record<string, unknown> | undefined))
  return {
    title: `${node.nodeKey} · ${node.name || node.nodeType}`,
    subtitle: `${card.chatflowName || card.sopId} · ${node.nodeType} · ${node.status}`,
    elapsedMs: numberValue(node.elapsedMs),
    input: node.inputs || {},
    output: node.outputs || {},
    usage,
    steps: [
      {
        id: node.nodeKey,
        label: node.name || node.nodeType,
        elapsedMs: numberValue(node.elapsedMs),
        input: node.inputs || {},
        output: node.outputs || {},
        usage,
      },
    ],
  }
}

export function buildRuntimeLabFunnelSummary(decision: RuntimeLabRouteDecision | null | undefined): RuntimeLabFunnelSummary {
  if (!decision) {
    return {
      stageLabel: '-',
      sourceLabel: '-',
      arbitratorLabel: '-',
    }
  }
  const stage = stringValue(decision.policyGate?.stage) || '-'
  const sources = decision.candidateSources?.length ? decision.candidateSources.join(', ') : '-'
  const mode = stringValue(decision.classifierResult?.arbitrator_mode)
  const usedRealLlm = decision.classifierResult?.used_real_llm === true
  const arbitrator = mode ? `${mode} · ${usedRealLlm ? 'real' : 'mock'}` : '-'
  return {
    stageLabel: stage,
    sourceLabel: sources,
    arbitratorLabel: arbitrator,
  }
}

export function buildRuntimeLabRouteOutcome(decision: RuntimeLabRouteDecision | null | undefined): RuntimeLabRouteOutcome | null {
  if (!decision) return null
  const finalDecision = objectValue(decision.finalDecision)
  if (decision.action === 'HANDOFF_TO_HUMAN') {
    return {
      tone: 'danger',
      title: '转人工',
      detail: routeReasonDetail(decision.handoff, finalDecision, decision.reason),
    }
  }
  if (decision.action === 'ANSWER_FAQ') {
    return {
      tone: 'success',
      title: 'FAQ命中',
      detail: routeReasonDetail(decision.faqAnswer, finalDecision, decision.reason),
    }
  }
  if (decision.action === 'ANSWER_RAG') {
    return {
      tone: 'success',
      title: 'RAG命中',
      detail: routeReasonDetail(decision.ragAnswer, finalDecision, decision.reason),
    }
  }
  if (decision.action === 'AGENT_FALLBACK') {
    return {
      tone: 'neutral',
      title: '兜底回答',
      detail: routeReasonDetail(decision.agentAnswer, finalDecision, decision.reason),
    }
  }
  if (decision.action === 'CLARIFY') {
    return {
      tone: 'warning',
      title: '需要澄清',
      detail: routeReasonDetail(decision.faqAnswer || decision.ragAnswer || decision.agentAnswer, finalDecision, decision.reason),
    }
  }
  return null
}

function routeReasonDetail(
  payload: Record<string, unknown> | null | undefined,
  finalDecision: Record<string, unknown> | null,
  fallbackReason: unknown,
) {
  const reasonCode = stringValue(payload?.reasonCode) || stringValue(finalDecision?.reasonCode)
  const sourceLayer = stringValue(payload?.sourceLayer) || stringValue(finalDecision?.sourceLayer)
  if (reasonCode && sourceLayer) return `${reasonCode} · ${sourceLayer}`
  if (reasonCode) return reasonCode
  if (sourceLayer) return sourceLayer
  return stringValue(fallbackReason) || '-'
}

export function runtimeLabPendingDelayMs(startedAt: number, now: number = Date.now()) {
  return Math.max(0, RUNTIME_LAB_MIN_PENDING_MS - Math.max(0, now - startedAt))
}

export function formatRuntimeLabUsage(usage: RuntimeLabUsage | undefined) {
  if (!usage) return 'in 0 / out 0 / total 0'
  const suffix = usage.estimated ? ' · est' : ''
  return `in ${usage.inputTokens} / out ${usage.outputTokens} / total ${usage.totalTokens}${suffix}`
}

export function formatRuntimeLabElapsed(elapsedMs: number | undefined) {
  const value = numberValue(elapsedMs)
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`
  return `${value}ms`
}

function buildRouteDebugDetail(turn: RuntimeLabTurn, elapsedMs: number): RuntimeLabDebugDetail {
  const classifierDebug = objectValue(turn.routeDecision.classifierResult?._debug)
  const routeUsage = normalizeUsage(classifierDebug?.usage)
  const steps = routeSteps(turn.routeDecision)
  const llmStep = classifierDebug
    ? [
        {
          id: 'llm_arbitrator_call',
          label: `LLM仲裁 · ${stringValue(classifierDebug.model) || 'model'}`,
          elapsedMs: numberValue(classifierDebug.elapsedMs),
          input: classifierDebug.input || {},
          output: classifierDebug.output || {},
          usage: routeUsage,
        },
      ]
    : []
  return {
    title: 'AI回复 · 路由调试',
    subtitle: `${turn.routeDecision.action}${turn.routeDecision.targetSopId ? ` · ${turn.routeDecision.targetSopId}` : ''}`,
    elapsedMs,
    input: turn.routeDecision.classifierRequest || classifierDebug?.input || {},
    output: classifierDebug?.output || turn.routeDecision.finalDecision || turn.routeDecision,
    usage: routeUsage,
    steps: [...steps, ...llmStep],
  }
}

function routeSteps(decision: RuntimeLabRouteDecision): RuntimeLabDebugStep[] {
  const policyGate = objectValue(decision.policyGate)
  const rawSteps = Array.isArray(policyGate?.steps) ? policyGate.steps : []
  return rawSteps.filter(isRecord).map((step, index) => ({
    id: stringValue(step.id) || stringValue(step.name) || `route_step_${index + 1}`,
    label: stringValue(step.label) || stringValue(step.name) || stringValue(step.stage) || `路由步骤 ${index + 1}`,
    elapsedMs: numberValue(step.elapsedMs),
    input: step.input || {},
    output: step.output || {},
    usage: normalizeUsage(step.usage),
  }))
}

function normalizeUsage(value: unknown): RuntimeLabUsage {
  const raw = objectValue(value)
  const inputTokens = usageNumber(raw, 'inputTokens', 'input_tokens', 'prompt_tokens', 'promptTokens')
    || estimateUsageTokens(raw?.promptChars)
  const outputTokens = usageNumber(raw, 'outputTokens', 'output_tokens', 'completion_tokens', 'completionTokens')
    || estimateUsageTokens(raw?.completionChars)
  const totalTokens = usageNumber(raw, 'totalTokens', 'total_tokens', 'totalTokens') || inputTokens + outputTokens
  return {
    inputTokens,
    outputTokens,
    totalTokens,
    estimated: raw?.estimated === true || Boolean(raw?.promptChars || raw?.completionChars),
  }
}

function usageNumber(raw: Record<string, unknown> | null, ...keys: string[]): number {
  if (!raw) return 0
  for (const key of keys) {
    const value = numberValue(raw[key])
    if (value > 0) return value
  }
  return 0
}

function estimateUsageTokens(value: unknown): number {
  const chars = numberValue(value)
  return chars > 0 ? Math.max(1, Math.round(chars / 4)) : 0
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0
}

function finiteNumber(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function objectValue(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function isCompletedNode(status: string) {
  return ['SUCCEEDED', 'COMPLETED', 'DONE'].includes(status.toUpperCase())
}

function isRunningNode(status: string) {
  return ['RUNNING', 'WAITING', 'INTERRUPTED'].includes(status.toUpperCase())
}

function displayValue(value: unknown) {
  if (value == null) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value
  return JSON.stringify(value)
}
