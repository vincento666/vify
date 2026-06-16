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

describe('workflow create Ant migration', () => {
  it('keeps workflow/chatflow canvas off Element Plus contracts', () => {
    const file = 'src/views/workflow/WorkflowCreate.vue'
    const content = readSource(file)
    const matches = [
      ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /<el-|<\/el-/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /\bEl[A-Z][A-Za-z]+/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /\.el-|--el-/g).map((match) => `${file} -> ${match[0]}`),
    ]

    expect(matches).toEqual([])
  })

  it('keeps the app entry free of the legacy route loader', () => {
    const main = readSource('src/main.ts')

    expect(main).not.toContain('legacy-element-plus')
    expect(main).not.toContain('requiresLegacyElementPlus')
    expect(main).not.toContain('installLegacyElementPlus')
  })

  it('exposes targeted test run controls for published versions', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const versionListStart = content.indexOf('data-testid="workflow-version-list"')
    const versionListEnd = content.indexOf('</section>', versionListStart)
    const versionList = content.slice(versionListStart, versionListEnd)

    expect(versionList).toContain('data-testid="workflow-version-run"')
    expect(versionList).toContain('runPublishedVersion(version.id)')
    expect(content).toContain('targetedPublishedRunResult')
    expect(content).toContain('versionId')
  })

  it('exposes a runtime v2 cancel control in the debug dock', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const dockStart = content.indexOf('data-testid="workflow-debug-dock"')
    const dockEnd = content.indexOf('data-testid="debug-error-panel"', dockStart)
    const debugDockHeader = content.slice(dockStart, dockEnd)

    expect(content).toContain('cancelRuntimeV2Run')
    expect(debugDockHeader).toContain('data-testid="debug-runtime-v2-cancel"')
    expect(debugDockHeader).toContain('aria-label="取消运行"')
    expect(debugDockHeader).toContain('@click="cancelCurrentRuntimeV2Run"')
  })
})
