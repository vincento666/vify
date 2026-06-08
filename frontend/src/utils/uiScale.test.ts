// @vitest-environment jsdom
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import {
  applyUiScaleToElement,
  classifyScaleDimension,
  createUiScaleSnapshot,
  toUiScaleCssVariables,
} from './uiScale'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

describe('hify ui scale foundation', () => {
  it('derives continuous desktop root font size from viewport width', () => {
    const width1280 = createUiScaleSnapshot(1280)
    const width1920 = createUiScaleSnapshot(1920)
    const width3840 = createUiScaleSnapshot(3840)

    expect(width1280.rootFontSize).toBe(14)
    expect(width1280.visualScale).toBe(0.875)
    expect(width1920.rootFontSize).toBe(16)
    expect(width1920.visualScale).toBe(1)
    expect(width3840.rootFontSize).toBe(24)
    expect(width3840.visualScale).toBe(1.5)
  })

  it('publishes stable hify css variables on a target element', () => {
    const element = document.createElement('html')
    const snapshot = applyUiScaleToElement(element, 2560)
    const vars = toUiScaleCssVariables(snapshot)

    expect(vars['--hify-root-font-size']).toBe('18.6672px')
    expect(vars['--hify-viewport-width']).toBe('2560px')
    expect(vars['--hify-scale']).toBe('1.1667')
    expect(element.style.getPropertyValue('--hify-root-font-size')).toBe('18.6672px')
    expect(element.dataset.hifyUiScale).toBe('ready')
  })

  it('classifies visual dimensions separately from geometry dimensions', () => {
    expect(classifyScaleDimension('card padding')).toBe('visual')
    expect(classifyScaleDimension('font size')).toBe('visual')
    expect(classifyScaleDimension('canvas coordinate')).toBe('geometry')
    expect(classifyScaleDimension('drag offset')).toBe('geometry')
    expect(classifyScaleDimension('dom measurement')).toBe('geometry')
  })

  it('binds root font size and base tokens to the rem scale contract', () => {
    const tokensCss = readProjectFile('src/styles/tokens.css')
    const globalCss = readProjectFile('src/styles/global.css')

    expect(tokensCss).toContain('--hify-root-font-size: 16px;')
    expect(tokensCss).toMatch(/--text-base:\s*0\.875rem;/)
    expect(tokensCss).toMatch(/--space-4:\s*1rem;/)
    expect(tokensCss).toMatch(/--radius-md:\s*0\.375rem;/)
    expect(tokensCss).toMatch(/--sidebar-width:\s*13\.75rem;/)
    expect(globalCss).toMatch(/html\s*\{[\s\S]*font-size:\s*var\(--hify-root-font-size\);/m)
  })
})
