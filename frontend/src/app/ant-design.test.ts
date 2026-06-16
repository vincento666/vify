import type { App } from 'vue'
import Antd from 'ant-design-vue'
import { describe, expect, it, vi } from 'vitest'

import { hifyAntTheme, installAntDesign } from './ant-design'

describe('Ant Design Vue app seam', () => {
  it('installs Ant Design Vue through the single app seam', () => {
    const app = { use: vi.fn() } as unknown as App<Element>

    installAntDesign(app)

    expect(app.use).toHaveBeenCalledWith(Antd)
  })

  it('bridges Hify design tokens into the Ant theme', () => {
    expect(hifyAntTheme.token.colorPrimary).toBe('#6366f1')
    expect(hifyAntTheme.token.colorSuccess).toBe('#10b981')
    expect(hifyAntTheme.token.fontFamily).toContain('PingFang SC')
  })
})
