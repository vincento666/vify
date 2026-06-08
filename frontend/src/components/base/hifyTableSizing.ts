export type ElementTableSize = number | string | undefined

export function normalizeElementTableSize(value: ElementTableSize, rootFontSize = currentRootFontSize()): ElementTableSize {
  if (typeof value !== 'string') return value
  const remMatch = value.trim().match(/^([0-9]*\.?[0-9]+)rem$/)
  if (!remMatch) return value
  return Math.round(Number(remMatch[1]) * rootFontSize)
}

function currentRootFontSize() {
  if (typeof window === 'undefined') return 16
  const parsed = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 16
}
