import { describe, expect, it } from 'vitest'

import { buildNodePaletteGroups, filterNodePaletteGroups } from './nodePalette'

describe('nodePalette', () => {
  it('uses a Coze-like compact category order without duplicate labels', () => {
    const groups = buildNodePaletteGroups('chatflow')

    expect(groups.map((group) => group.title)).toEqual(['资源', '业务逻辑', '输入&输出', '知识库'])
    expect(groups[0].items.slice(0, 3).map((item) => item.label)).toEqual(['大模型', '插件', '工作流'])

    const labels = groups.flatMap((group) => group.items.map((item) => item.label))
    expect(new Set(labels).size).toBe(labels.length)
  })

  it('keeps task workflow palette free of conversation-only nodes', () => {
    const labels = buildNodePaletteGroups('workflow').flatMap((group) => group.items.map((item) => item.label))

    expect(labels).toContain('大模型')
    expect(labels).toContain('工作流')
    expect(labels).toContain('智能体')
    expect(labels).toContain('变量聚合')
    expect(labels).not.toContain('消息')
    expect(labels).not.toContain('问题')
    expect(labels).not.toContain('信息收集')
    expect(labels).not.toContain('转人工')
  })

  it('searches by concise labels and aliases while preserving group order', () => {
    const groups = buildNodePaletteGroups('workflow')

    expect(filterNodePaletteGroups(groups, '条件')).toEqual([
      {
        title: '业务逻辑',
        items: [expect.objectContaining({ type: 'CONDITION', label: '选择器' })],
      },
    ])
    expect(filterNodePaletteGroups(groups, 'mcp')[0].items).toEqual([
      expect.objectContaining({ type: 'TOOL_CALL', label: '插件' }),
    ])
  })
})
