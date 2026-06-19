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

function sourceSection(content: string, startMarker: string, endMarker: string) {
  const start = content.indexOf(startMarker)
  const end = content.indexOf(endMarker, start)
  return content.slice(start, end)
}

describe('workflow Phase 9 UX convergence', () => {
  it('keeps waiting summary business-facing before advanced debug detail', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const waitingSummary = sourceSection(
      content,
      'data-testid="chatflow-waiting-state"',
      'data-testid="chatflow-debug-advanced"',
    )

    expect(waitingSummary).not.toContain('Checkpoint #')
    expect(waitingSummary).not.toContain('Event #')
    expect(waitingSummary).toContain('请按下方表单补充信息')
  })

  it('keeps version test result copy product-worded instead of runtime/debug refs', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const versionList = sourceSection(content, 'data-testid="workflow-version-list"', '</section>')

    expect(versionList).toContain('实时测试')
    expect(versionList).not.toContain('Runtime v2 测试')
    expect(content).not.toContain('Runtime v2 版本 v')
    expect(versionList).not.toContain('debugRef')
    expect(content).toContain('实时运行版本 v')
  })
})
