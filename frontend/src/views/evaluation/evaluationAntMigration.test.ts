import { describe, expect, it } from 'vitest'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

const vueFiles = [
  'CompareAnalysisPanel.vue',
  'EvalSetDetail.vue',
  'EvalSetsPanel.vue',
  'EvaluationWorkbench.vue',
  'EvaluatorsPanel.vue',
  'ExperimentsPanel.vue',
  'RunRecordsPanel.vue',
]

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('evaluation Ant Design migration guard', () => {
  it('keeps evaluation Vue files free of Element Plus primitives', () => {
    const offenders = vueFiles.flatMap((file) => {
      const content = readProjectFile(`src/views/evaluation/${file}`)
      return [
        ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /<el-|<\/el-/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /\.el-|--el-/g).map((match) => `${file} -> ${match[0]}`),
        ...regexMatches(content, /\bElMessage\b|\bElMessageBox\b|window\.confirm/g).map((match) => `${file} -> ${match[0]}`),
      ]
    })

    expect(offenders).toEqual([])
  })
})
