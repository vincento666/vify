// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('Knowledge pages Ant Design Vue migration', () => {
  it('keeps knowledge list/detail pages off Element Plus contracts', () => {
    const files = [
      'src/views/knowledge/KnowledgeList.vue',
      'src/views/knowledge/DocumentList.vue',
    ]
    const matches = files.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /<el-/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /\.el-|--el-/g).map((match) => `${file} -> ${match[0]}`),
      ]
    })

    expect(matches).toEqual([])
  })
})
