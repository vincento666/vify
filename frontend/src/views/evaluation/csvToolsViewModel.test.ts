// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { acceptedCsvName, csvImportHint } from './csvToolsViewModel'

describe('csv tools view model', () => {
  it('accepts csv filenames and explains required columns', () => {
    expect(acceptedCsvName('cases.csv')).toBe(true)
    expect(acceptedCsvName('cases.txt')).toBe(false)
    expect(csvImportHint()).toContain('input、expectedOutput、tags')
  })
})
