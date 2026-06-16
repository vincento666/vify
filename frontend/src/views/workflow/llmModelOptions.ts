import type { ProviderVO } from '@/api/provider'

export type LlmModelOption = {
  provider: string
  providerType: string
  providerIconKey: string
  value: string
  label: string
  description: string
  enabled: boolean
  providerId?: number
  modelConfigId?: number
}

type LlmModelFamily = 'qwen' | 'deepseek' | 'mimo'

const modelFamilyDescriptions: Record<LlmModelFamily, string> = {
  qwen: '通义千问系列模型，适合中文理解、推理和工具调用。',
  deepseek: 'DeepSeek 系列模型，适合推理、代码和通用对话。',
  mimo: '小米 MiMo 系列模型，适合轻量快速的通用任务。',
}

export function buildLlmModelOptions(providers: ProviderVO[]): LlmModelOption[] {
  const seen = new Set<string>()
  const options: LlmModelOption[] = []
  providers.forEach((provider) => {
    if (!provider.enabled || !provider.authConfigured || provider.baseUrl.startsWith('mock://')) return
    provider.models
      .filter((model) => model.enabled)
      .forEach((model) => {
        const modelFamily = supportedModelFamily(provider.name, model.name, model.modelId, model.displayName)
        if (!modelFamily) return
        const key = model.modelId.trim().toLowerCase()
        if (seen.has(key)) return
        seen.add(key)
        options.push({
          provider: provider.name,
          providerType: provider.type,
          providerIconKey: modelProviderIconKey(provider.name, provider.type),
          providerId: provider.id,
          modelConfigId: model.id,
          value: model.modelId,
          label: model.displayName || model.name || model.modelId,
          description: modelDescription(model, modelFamily),
          enabled: true,
        })
      })
  })
  return options
}

export function supportedModelFamily(
  providerName: string,
  modelName: string,
  modelId: string,
  displayName = '',
): LlmModelFamily | null {
  const source = `${modelId} ${displayName} ${modelName} ${providerName}`.toLowerCase()
  if (source.includes('qwen') || source.includes('通义') || source.includes('千问')) return 'qwen'
  if (source.includes('deepseek')) return 'deepseek'
  if (source.includes('mimo') || source.includes('xiaomi') || source.includes('小米')) return 'mimo'
  return null
}

export function modelProviderIconKey(providerName: string, providerType: string, modelId = '') {
  const type = providerType.trim().toUpperCase()
  if (type === 'OPENAI' || type === 'OPENAI_COMPATIBLE') return 'openai'
  if (type === 'ANTHROPIC') return 'anthropic'
  if (type === 'GEMINI' || type === 'GOOGLE') return 'gemini'
  if (type === 'AZURE_OPENAI' || type === 'AZURE') return 'azure'
  if (type === 'OLLAMA') return 'ollama'
  if (type === 'DEEPSEEK') return 'openai'
  const source = `${providerName} ${providerType} ${modelId}`.toLowerCase()
  if (source.includes('anthropic') || source.includes('claude')) return 'anthropic'
  if (source.includes('gemini') || source.includes('google')) return 'gemini'
  if (source.includes('azure')) return 'azure'
  if (source.includes('ollama')) return 'ollama'
  if (source.includes('openai') || source.includes('openrouter')) return 'openai'
  return 'compatible'
}

function modelDescription(model: { modelId: string; description?: string }, modelFamily: LlmModelFamily) {
  const description = String(model.description || '').trim()
  return description || modelFamilyDescriptions[modelFamily] || `模型 ID：${model.modelId}`
}

export function llmModelSelectionFields(option: LlmModelOption) {
  return {
    model: option.value,
    modelConfigId: option.modelConfigId,
    providerId: option.providerId,
  }
}
