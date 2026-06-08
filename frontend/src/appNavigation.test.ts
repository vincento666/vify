import { describe, expect, it } from 'vitest'

import { composerNavItems } from './appNavigation'

describe('composer navigation', () => {
  it('keeps run debugging inside composer surfaces instead of exposing Observe as a top-level product module', () => {
    const labels = composerNavItems.map((item) => item.label)
    const paths = composerNavItems.map((item) => item.path)

    expect(labels).not.toContain('观测')
    expect(paths).not.toContain('/observe')
    expect(labels).toEqual(expect.arrayContaining(['工作流', 'Agent', '评测']))
  })
})
