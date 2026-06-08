import { describe, expect, it } from 'vitest'
import { normalizeElementTableSize } from './hifyTableSizing'

describe('HifyTable sizing bridge', () => {
  it('converts rem column widths to numeric pixel values for Element Plus tables', () => {
    expect(normalizeElementTableSize('8.75rem', 16)).toBe(140)
    expect(normalizeElementTableSize('5rem', 16)).toBe(80)
    expect(normalizeElementTableSize('10rem', 14)).toBe(140)
  })

  it('keeps numeric and non-rem sizes unchanged', () => {
    expect(normalizeElementTableSize(120, 16)).toBe(120)
    expect(normalizeElementTableSize('100%', 16)).toBe('100%')
    expect(normalizeElementTableSize(undefined, 16)).toBeUndefined()
  })
})
