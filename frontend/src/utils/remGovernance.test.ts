// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('hify rem governance', () => {
  it('keeps app shell and base components off raw visual px sizing', () => {
    const files = [
      'src/App.vue',
      'src/components/base/HifyFormDialog.vue',
      'src/components/base/HifyTable.vue',
    ]
    const visualPxPattern = /\b(?:font-size|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|width|height|border-radius|left|top|right|bottom)\s*:\s*(?!1px\b)[^;\n]*\bpx\b/g
    const stringDefaultPxPattern = /\b(?:width|labelWidth):\s*'[^']*px'/g
    const fixedIconSizePattern = /:size="\d+"/g

    const matches = files.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...collectMatches(content, visualPxPattern),
        ...collectMatches(content, stringDefaultPxPattern),
        ...(file === 'src/App.vue' ? collectMatches(content, fixedIconSizePattern) : []),
      ].map((match) => `${file} -> ${match}`)
    })

    expect(matches).toEqual([])
  })

  it('bridges Ant Design Vue component sizing through hify theme tokens', () => {
    const antDesign = readProjectFile('src/app/ant-design.ts')

    expect(antDesign).toContain('hifyAntTheme')
    expect(antDesign).toContain('borderRadius: 6')
    expect(antDesign).toContain('fontSize: 14')
    expect(antDesign).toContain('PingFang SC')
  })
})
