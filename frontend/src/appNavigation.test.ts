// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { composerNavItems } from './appNavigation'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSourceFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('composer navigation', () => {
  it('keeps run debugging inside composer surfaces instead of exposing Observe as a top-level product module', () => {
    const labels = composerNavItems.map((item) => item.label)
    const paths = composerNavItems.map((item) => item.path)

    expect(labels).not.toContain('观测')
    expect(paths).not.toContain('/observe')
    expect(labels).toEqual(expect.arrayContaining(['工作流', 'Agent', '评测']))
  })

  it('uses Ant Design Vue shell primitives instead of Element Plus shell contracts', () => {
    const files = ['src/App.vue', 'src/appNavigation.ts']
    const matches = files.flatMap((file) => {
      const content = readSourceFile(file)
      return [
        ...regexMatches(content, /@element-plus\/icons-vue/g).map(() => `${file} -> @element-plus/icons-vue`),
        ...regexMatches(content, /<el-(?:icon|tooltip|avatar)/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /--el-/g).map(() => `${file} -> --el-`),
      ]
    })

    expect(matches).toEqual([])
  })
})
