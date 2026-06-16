import { describe, expect, it } from 'vitest'

import type { ProviderVO } from '@/api/provider'
import { buildLlmModelOptions, llmModelSelectionFields } from './llmModelOptions'

const provider = (overrides: Partial<ProviderVO>): ProviderVO => ({
  id: 1,
  name: 'OpenRouter',
  type: 'OPENAI_COMPATIBLE',
  baseUrl: 'https://openrouter.ai/api/v1',
  description: '',
  enabled: true,
  authConfigured: true,
  createdAt: '',
  updatedAt: '',
  health: null,
  models: [],
  ...overrides,
})

describe('workflow llm model options', () => {
  it('uses provider model config ids instead of saving model names alone', () => {
    const options = buildLlmModelOptions([
      provider({
        id: 665,
        models: [
          { id: 607, name: 'Xiaomi MiMo v2 Flash', modelId: 'xiaomi/mimo-v2-flash', displayName: 'MiMo Flash', enabled: true },
          { id: 610, name: 'GPT-4o', modelId: 'gpt-4o', displayName: 'GPT-4o', enabled: true },
          { id: 611, name: 'bad-model', modelId: 'bad-model', displayName: 'bad-model', enabled: true },
          { id: 608, name: 'Disabled model', modelId: 'disabled/model', enabled: false },
        ],
      }),
      provider({
        id: 666,
        name: 'Mock',
        baseUrl: 'mock://provider',
        models: [
          { id: 609, name: 'Mock model', modelId: 'mock/model', enabled: true },
        ],
      }),
    ])

    expect(options).toEqual([
      expect.objectContaining({
        provider: 'OpenRouter',
        providerType: 'OPENAI_COMPATIBLE',
        providerIconKey: 'openai',
        providerId: 665,
        modelConfigId: 607,
        value: 'xiaomi/mimo-v2-flash',
        label: 'MiMo Flash',
        description: '小米 MiMo 系列模型，适合轻量快速的通用任务。',
        enabled: true,
      }),
    ])
    expect(llmModelSelectionFields(options[0])).toEqual({
      model: 'xiaomi/mimo-v2-flash',
      modelConfigId: 607,
      providerId: 665,
    })
  })

  it('keeps only qwen deepseek and mimo family models and deduplicates by model id', () => {
    const options = buildLlmModelOptions([
      provider({
        id: 11,
        name: 'Old OpenRouter',
        models: [
          { id: 101, name: 'qwen old', modelId: 'qwen/qwen3.5-9b', enabled: true },
          { id: 102, name: 'deepseek old', modelId: 'deepseek/deepseek-v4-flash', enabled: true },
          { id: 103, name: 'mimo old', modelId: 'xiaomi/mimo-v2-flash', enabled: true },
          { id: 104, name: 'GPT-4o', modelId: 'gpt-4o', enabled: true },
        ],
      }),
      provider({
        id: 12,
        name: 'Fresh OpenRouter',
        models: [
          { id: 201, name: 'qwen latest', modelId: 'qwen/qwen3.5-9b', enabled: true },
          { id: 202, name: 'probe', modelId: 'probe-model', enabled: true },
          { id: 203, name: 'bad', modelId: 'bad-model', enabled: true },
        ],
      }),
    ])

    expect(options.map((option) => option.value)).toEqual([
      'qwen/qwen3.5-9b',
      'deepseek/deepseek-v4-flash',
      'xiaomi/mimo-v2-flash',
    ])
    expect(options.map((option) => option.providerIconKey)).toEqual(['openai', 'openai', 'openai'])
  })

  it('uses integration protocol type for provider icons instead of model vendor names', () => {
    const options = buildLlmModelOptions([
      provider({
        id: 21,
        name: 'Any OpenAI Compatible Gateway',
        type: 'OPENAI_COMPATIBLE',
        models: [
          { id: 301, name: 'custom qwen', modelId: 'tenant/qwen-private', enabled: true },
        ],
      }),
      provider({
        id: 22,
        name: 'Anthropic Native',
        type: 'ANTHROPIC',
        models: [
          { id: 302, name: 'custom deepseek through anthropic router', modelId: 'tenant/deepseek-private', enabled: true },
        ],
      }),
    ])

    expect(options.map((option) => option.providerIconKey)).toEqual(['openai', 'anthropic'])
  })
})
