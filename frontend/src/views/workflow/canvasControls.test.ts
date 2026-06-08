import { describe, expect, it } from 'vitest'

import {
  CANVAS_CONNECTION_RADIUS,
  CANVAS_ENDPOINT_BASE_DIAMETER_REM,
  CANVAS_ENDPOINT_CONNECTED_SCALE,
  CANVAS_ENDPOINT_HIT_DIAMETER_REM,
  CANVAS_ENDPOINT_HOVER_SCALE,
  CANVAS_ENDPOINT_PREVIEW_RADIUS,
  CANVAS_NODE_HOVER_ENDPOINT_SCALE,
  CANVAS_PANE_CLICK_DISTANCE,
  CANVAS_TRACKPAD_PAN_SPEED,
  CANVAS_ZOOM_ANIMATION_MS,
  CANVAS_ZOOM_PRESETS,
  clampCanvasZoom,
  formatCanvasZoomLabel,
  nextCanvasZoom,
  normalizeCanvasOperationMode,
  operationModeTitle,
} from './canvasControls'

describe('workflow canvas controls', () => {
  it('uses the requested common zoom presets and labels them as percentages', () => {
    expect(CANVAS_ZOOM_PRESETS).toEqual([0.25, 0.5, 0.75, 1, 1.25, 1.5])
    expect(formatCanvasZoomLabel(0.25)).toBe('25%')
    expect(formatCanvasZoomLabel(1.5)).toBe('150%')
  })

  it('steps zoom buttons through presets while clamping to supported bounds', () => {
    expect(nextCanvasZoom(1, 'in')).toBe(1.25)
    expect(nextCanvasZoom(1, 'out')).toBe(0.75)
    expect(nextCanvasZoom(1.49, 'in')).toBe(1.5)
    expect(nextCanvasZoom(0.26, 'out')).toBe(0.25)
    expect(clampCanvasZoom(0.1)).toBe(0.25)
    expect(clampCanvasZoom(1.8)).toBe(1.5)
  })

  it('normalizes persisted operation mode and exposes Chinese titles', () => {
    expect(normalizeCanvasOperationMode('trackpad')).toBe('trackpad')
    expect(normalizeCanvasOperationMode('bad')).toBe('mouse')
    expect(operationModeTitle('mouse')).toBe('鼠标模式')
    expect(operationModeTitle('trackpad')).toBe('触控板模式')
  })

  it('keeps canvas gestures responsive without noisy accidental clicks', () => {
    expect(CANVAS_TRACKPAD_PAN_SPEED).toBeGreaterThan(0.5)
    expect(CANVAS_TRACKPAD_PAN_SPEED).toBeLessThanOrEqual(1.2)
    expect(CANVAS_ZOOM_ANIMATION_MS).toBeLessThanOrEqual(90)
    expect(CANVAS_PANE_CLICK_DISTANCE).toBeGreaterThanOrEqual(3)
  })

  it('uses the magnetic connection radius for endpoint hover and preview affordances', () => {
    expect(CANVAS_ENDPOINT_PREVIEW_RADIUS).toBe(CANVAS_CONNECTION_RADIUS)
    expect(CANVAS_ENDPOINT_BASE_DIAMETER_REM).toBe(0.75)
    expect(CANVAS_NODE_HOVER_ENDPOINT_SCALE).toBe(2)
    expect(CANVAS_ENDPOINT_HOVER_SCALE).toBe(3)
    expect(CANVAS_ENDPOINT_CONNECTED_SCALE).toBe(3)
    expect(CANVAS_ENDPOINT_HIT_DIAMETER_REM).toBeCloseTo(7.3333, 4)
  })
})
