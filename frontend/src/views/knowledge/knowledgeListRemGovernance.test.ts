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

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('knowledge list rem governance', () => {
  it('keeps knowledge list visual sizing on rem tokens', () => {
    const content = readProjectFile('src/views/knowledge/KnowledgeList.vue')
    const rawVisualPxPattern = /\b(?:font-size|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|min-width|max-width|min-height|max-height|width|height|border-radius|transform)\s*:\s*(?!1px\b)[^;\n]*\bpx\b/g
    const templatePxPattern = /(?:width|label-width)="[0-9.]+px"|:width="[0-9.]+\"|:size="[0-9.]+\"|style="[^"]*[0-9.]+px/g

    const matches = [
      ...collectMatches(content, rawVisualPxPattern),
      ...collectMatches(content, templatePxPattern),
    ]

    expect(matches).toEqual([])
  })

  it('keeps the knowledge list copy business-facing', () => {
    const content = readProjectFile('src/views/knowledge/KnowledgeList.vue')

    expect(content).toContain('沉淀业务资料')
    expect(content).toContain('可回答内容')
    expect(content).not.toContain('RAG')
    expect(content).not.toContain('向量化')
    expect(content).not.toContain('召回')
  })
})
