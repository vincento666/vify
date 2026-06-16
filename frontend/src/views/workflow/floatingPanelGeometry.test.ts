import { describe, expect, it } from 'vitest'

import { computeVariableFlyoutPosition } from './floatingPanelGeometry'

describe('workflow floating panel geometry', () => {
  it('keeps variable flyout separated from the source list panel', () => {
    const result = computeVariableFlyoutPosition({
      triggerRect: { left: 340, right: 380, top: 160, bottom: 192 },
      sourcePanelRect: { left: 120, right: 400, top: 120, bottom: 480 },
      viewportWidth: 960,
      viewportHeight: 720,
      flyoutWidth: 296,
      flyoutMaxHeight: 304,
      gap: 8,
      padding: 12,
      rem: 16,
    })

    expect(result.placement).toBe('right')
    expect(result.left).toBe(408)
    expect(result.left).toBeGreaterThanOrEqual(400 + 8)
  })
})
