import { describe, expect, it } from 'vitest'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('runtime lab Ant Design migration guard', () => {
  it('keeps the unified routing lab free of Element Plus primitives', () => {
    const content = readProjectFile('src/views/chat/UnifiedRoutingChatLab.vue')

    const offenders = [
      ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => match[0]),
      ...regexMatches(content, /<el-|<\/el-/g).map((match) => match[0]),
      ...regexMatches(content, /\.el-|--el-/g).map((match) => match[0]),
      ...regexMatches(content, /\bElMessage\b|\bElMessageBox\b|window\.confirm/g).map((match) => match[0]),
    ]

    expect(offenders).toEqual([])
    expect(content).toContain("from 'ant-design-vue'")
    expect(content).toContain("from '@ant-design/icons-vue'")
  })
})
