export interface UiScaleConfig {
  minWidth: number
  baseWidth: number
  maxWidth: number
  minScale: number
  maxScale: number
  minFontScale: number
  maxFontScale: number
  minSpaceScale: number
  maxSpaceScale: number
  minControlScale: number
  maxControlScale: number
  minPanelScale: number
  maxPanelScale: number
  baseRootFontSize: number
}

export interface UiScaleSnapshot {
  rawWidth: number
  viewportWidth: number
  visualScale: number
  fontScale: number
  spaceScale: number
  controlScale: number
  panelScale: number
  rootFontSize: number
}

export type ScaleDimensionKind = 'visual' | 'geometry'

export const geometrySizeWhitelist = [
  'canvas-coordinate',
  'edge-control-point',
  'drag-offset',
  'dom-measurement',
  'handle-hit-area',
  'floating-layer-position',
  'vue-flow-viewport',
] as const

const geometryContextKeywords = [
  'canvas',
  'coordinate',
  'coords',
  'position',
  'floating',
  'offset',
  'drag',
  'path',
  'control point',
  'measurement',
  'measure',
  'rect',
  'bounds',
  'hit area',
  'handle',
  'viewport',
  'translate',
] as const

export const uiScaleConfig: UiScaleConfig = {
  minWidth: 1280,
  baseWidth: 1920,
  maxWidth: 3840,
  minScale: 0.875,
  maxScale: 1.5,
  minFontScale: 0.92,
  maxFontScale: 1.32,
  minSpaceScale: 0.875,
  maxSpaceScale: 1.5,
  minControlScale: 0.9,
  maxControlScale: 1.2,
  minPanelScale: 0.95,
  maxPanelScale: 1.12,
  baseRootFontSize: 16,
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function roundScale(value: number) {
  return Number(value.toFixed(4))
}

function normalizeContext(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
}

function interpolateScale(
  width: number,
  config: UiScaleConfig,
  minValue: number,
  maxValue: number,
) {
  const clampedWidth = clamp(width, config.minWidth, config.maxWidth)

  if (clampedWidth <= config.baseWidth) {
    if (config.baseWidth === config.minWidth) return 1
    const progress = (clampedWidth - config.minWidth) / (config.baseWidth - config.minWidth)
    return minValue + (1 - minValue) * progress
  }

  if (config.maxWidth === config.baseWidth) return 1

  const progress = (clampedWidth - config.baseWidth) / (config.maxWidth - config.baseWidth)
  return 1 + (maxValue - 1) * progress
}

export function isGeometrySizeCategory(category: string) {
  const normalizedCategory = normalizeContext(category)
  return geometrySizeWhitelist.some((item) => normalizeContext(item) === normalizedCategory)
}

export function classifyScaleDimension(context: string): ScaleDimensionKind {
  const normalizedContext = normalizeContext(context)

  if (!normalizedContext) return 'visual'
  if (isGeometrySizeCategory(normalizedContext)) return 'geometry'

  return geometryContextKeywords.some((keyword) => normalizedContext.includes(keyword))
    ? 'geometry'
    : 'visual'
}

export function createUiScaleSnapshot(
  width: number,
  config: UiScaleConfig = uiScaleConfig,
): UiScaleSnapshot {
  const viewportWidth = clamp(width, config.minWidth, config.maxWidth)
  const visualScale = roundScale(interpolateScale(viewportWidth, config, config.minScale, config.maxScale))

  return {
    rawWidth: width,
    viewportWidth,
    visualScale,
    fontScale: roundScale(interpolateScale(viewportWidth, config, config.minFontScale, config.maxFontScale)),
    spaceScale: roundScale(interpolateScale(viewportWidth, config, config.minSpaceScale, config.maxSpaceScale)),
    controlScale: roundScale(interpolateScale(viewportWidth, config, config.minControlScale, config.maxControlScale)),
    panelScale: roundScale(interpolateScale(viewportWidth, config, config.minPanelScale, config.maxPanelScale)),
    rootFontSize: roundScale(config.baseRootFontSize * visualScale),
  }
}

export function toUiScaleCssVariables(snapshot: UiScaleSnapshot) {
  return {
    '--hify-scale': snapshot.visualScale.toFixed(4),
    '--hify-font-scale': snapshot.fontScale.toFixed(4),
    '--hify-space-scale': snapshot.spaceScale.toFixed(4),
    '--hify-control-scale': snapshot.controlScale.toFixed(4),
    '--hify-panel-scale': snapshot.panelScale.toFixed(4),
    '--hify-root-font-size': `${snapshot.rootFontSize}px`,
    '--hify-viewport-width': `${snapshot.viewportWidth}px`,
  }
}

export function applyUiScaleToElement(
  element: HTMLElement,
  width: number,
  config: UiScaleConfig = uiScaleConfig,
) {
  const snapshot = createUiScaleSnapshot(width, config)
  const cssVariables = toUiScaleCssVariables(snapshot)

  Object.entries(cssVariables).forEach(([key, value]) => {
    element.style.setProperty(key, value)
  })
  element.dataset.hifyUiScale = 'ready'
  return snapshot
}
