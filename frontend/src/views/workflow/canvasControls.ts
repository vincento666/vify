export type CanvasOperationMode = 'mouse' | 'trackpad'
export type CanvasZoomDirection = 'in' | 'out'

export const CANVAS_ZOOM_PRESETS = [0.25, 0.5, 0.75, 1, 1.25, 1.5] as const
export const CANVAS_ZOOM_MIN = CANVAS_ZOOM_PRESETS[0]
export const CANVAS_ZOOM_MAX = CANVAS_ZOOM_PRESETS[CANVAS_ZOOM_PRESETS.length - 1]
export const CANVAS_TRACKPAD_PAN_SPEED = 0.9
export const CANVAS_ZOOM_ANIMATION_MS = 80
export const CANVAS_PANE_CLICK_DISTANCE = 4
export const CANVAS_CONNECTION_RADIUS = 18
export const CANVAS_ENDPOINT_PREVIEW_RADIUS = CANVAS_CONNECTION_RADIUS
export const CANVAS_ENDPOINT_BASE_DIAMETER_REM = 1
export const CANVAS_ENDPOINT_HIT_AREA_SCALE = 3
export const CANVAS_NODE_HOVER_ENDPOINT_SCALE = 1
export const CANVAS_ENDPOINT_HOVER_SCALE = 1.2
export const CANVAS_ENDPOINT_CONNECTED_SCALE = CANVAS_ENDPOINT_HOVER_SCALE
export const CANVAS_ENDPOINT_HIT_DIAMETER_REM = CANVAS_ENDPOINT_BASE_DIAMETER_REM * CANVAS_ENDPOINT_HIT_AREA_SCALE

export function clampCanvasZoom(zoom: number) {
  if (!Number.isFinite(zoom)) return 1
  return Math.min(CANVAS_ZOOM_MAX, Math.max(CANVAS_ZOOM_MIN, Number(zoom.toFixed(3))))
}

export function formatCanvasZoomLabel(zoom: number) {
  return `${Math.round(clampCanvasZoom(zoom) * 100)}%`
}

export function nextCanvasZoom(currentZoom: number, direction: CanvasZoomDirection) {
  const current = clampCanvasZoom(currentZoom)
  if (direction === 'in') {
    return CANVAS_ZOOM_PRESETS.find((preset) => preset > current + 0.001) ?? CANVAS_ZOOM_MAX
  }
  return [...CANVAS_ZOOM_PRESETS].reverse().find((preset) => preset < current - 0.001) ?? CANVAS_ZOOM_MIN
}

export function normalizeCanvasOperationMode(value: unknown): CanvasOperationMode {
  return value === 'trackpad' ? 'trackpad' : 'mouse'
}

export function operationModeTitle(mode: CanvasOperationMode) {
  return mode === 'trackpad' ? '触控板模式' : '鼠标模式'
}
