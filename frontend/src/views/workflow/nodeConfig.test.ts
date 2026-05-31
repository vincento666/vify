import { describe, expect, it } from 'vitest'

import { applyNodeConfigPatch, getNodeConfigSchema } from './nodeConfig'

describe('workflow node config schema', () => {
  it('provides runtime-backed editable fields for each canvas node type', () => {
    expect(getNodeConfigSchema('START').sections.map((section) => section.title)).toEqual(['基础信息', '输入变量'])
    expect(getNodeConfigSchema('LLM').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['prompt', 'outputVariable']),
    )
    expect(getNodeConfigSchema('CONDITION').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['expression', 'outputVariable']),
    )
    expect(getNodeConfigSchema('KNOWLEDGE').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['knowledgeBaseId', 'topK', 'outputVariable']),
    )
    expect(getNodeConfigSchema('API_CALL').sections.flatMap((section) => section.fields.map((field) => field.key))).toEqual(
      expect.arrayContaining(['endpoint', 'method', 'outputVariable']),
    )
    expect(getNodeConfigSchema('END').sections.flatMap((section) => section.fields.map((field) => field.key))).toContain(
      'outputVariable',
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
})
