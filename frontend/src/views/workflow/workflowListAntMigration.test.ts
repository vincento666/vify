// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readSource(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('workflow list Ant migration', () => {
  it('keeps workflow/chatflow list shell off Element Plus contracts', () => {
    const files = [
      'src/views/workflow/WorkflowModuleTabs.vue',
      'src/views/workflow/WorkflowList.vue',
      'src/views/workflow/ChatflowList.vue',
    ]

    const matches = files.flatMap((file) => {
      const content = readSource(file)
      return [
        ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /<el-|<\/el-/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /\.el-|--el-/g).map((match) => `${file} -> ${match[0]}`),
      ]
    })

    expect(matches).toEqual([])
  })
})
