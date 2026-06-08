// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

const governedFiles = [
  'src/views/mcp/McpServerList.vue',
  'src/views/workflow/WorkflowList.vue',
  'src/views/workflow/ChatflowList.vue',
  'src/views/evaluation/EvaluationWorkbench.vue',
  'src/views/evaluation/ExperimentsPanel.vue',
  'src/views/evaluation/EvalSetsPanel.vue',
  'src/views/evaluation/EvaluatorsPanel.vue',
  'src/views/evaluation/RunRecordsPanel.vue',
  'src/views/evaluation/CompareAnalysisPanel.vue',
]

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('management page rem governance', () => {
  it('keeps remaining list and evaluation surfaces on rem visual sizing', () => {
    const rawVisualPxPattern = /(?<![-\w])(?:font-size|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|grid-template-columns|min-width|max-width|min-height|max-height|width|height|border-radius|top|right|bottom|left)\s*:\s*(?!1px\b)[^;\n]*px\b/g
    const templateVisualSizePattern = /(?<![-:])(?:width|min-width|max-width|label-width|size)="[0-9.]+(?:px)?"|:(?:width|min-width|max-width|size)="[0-9.]+"|style="[^"]*[0-9.]+px/g

    const matches = governedFiles.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...collectMatches(content, rawVisualPxPattern),
        ...collectMatches(content, templateVisualSizePattern),
      ].map((match) => `${file}: ${match}`)
    })

    expect(matches).toEqual([])
  })
})
