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

function extractHeaderBlock(content: string, className: string) {
  const pattern = new RegExp(`<header[^>]+class="${className}"[^>]*>[\\s\\S]*?<\\/header>`)
  return content.match(pattern)?.[0] || ''
}

describe('evaluation workbench primary actions', () => {
  it('keeps experiment creation as the Experiments tab action instead of duplicating it in the page header', () => {
    const workbench = readProjectFile('src/views/evaluation/EvaluationWorkbench.vue')
    const experimentsPanel = readProjectFile('src/views/evaluation/ExperimentsPanel.vue')
    const header = extractHeaderBlock(workbench, 'evaluation-header')

    expect(header).not.toContain('<el-button')
    expect(experimentsPanel.match(/data-testid="create-experiment"/g)).toHaveLength(1)
  })

  it('keeps run-record filters as filters instead of a third navigation layer', () => {
    const runRecordsPanel = readProjectFile('src/views/evaluation/RunRecordsPanel.vue')

    expect(runRecordsPanel).not.toContain('<el-segmented')
    expect(runRecordsPanel).toContain('data-testid="run-status-filter"')
    expect(runRecordsPanel).toContain('data-testid="case-status-filter"')
  })

  it('keeps Eval Set list as an object list instead of embedding the detail tabs below it', () => {
    const evalSetsPanel = readProjectFile('src/views/evaluation/EvalSetsPanel.vue')

    expect(evalSetsPanel).not.toContain('class="eval-set-detail-tabs"')
    expect(evalSetsPanel).not.toContain('data-testid="related-experiments-panel"')
    expect(evalSetsPanel).toContain('data-testid="view-eval-set-detail"')
  })

  it('keeps Eval Set detail readable with a path header and CSS-owned table sizing', () => {
    const detail = readProjectFile('src/views/evaluation/EvalSetDetail.vue')

    expect(detail).toContain('data-testid="eval-set-detail-breadcrumb"')
    expect(detail).toContain('评测集')
    expect(detail).not.toMatch(/<el-table-column[^>]+(?:min-width|width)="[0-9.]+rem"/)
    expect(detail).toContain('class-name="related-target-column"')
    expect(detail).toContain('class-name="related-status-column"')
  })

  it('keeps Eval Set detail actions object-first instead of exposing implementation controls', () => {
    const detail = readProjectFile('src/views/evaluation/EvalSetDetail.vue')

    expect(detail).toContain('data-testid="eval-set-detail-overview"')
    expect(detail).toContain('data-testid="import-eval-cases"')
    expect(detail).toContain('ref="csvInput"')
    expect(detail).toContain('class="csv-file-input"')
    expect(detail).not.toContain('<input data-testid="csv-import-input" type="file"')
    expect(detail).not.toContain('csv-hint')
    expect(detail).not.toContain('@click="router.push(\'/evaluation\')">评测</button>')
  })

  it('uses only the object breadcrumb on Eval Set detail pages', () => {
    const app = readProjectFile('src/App.vue')
    const router = readProjectFile('src/router/index.ts')

    expect(router).toContain("hideShellBreadcrumb: true")
    expect(app).toContain('hideShellBreadcrumb')
    expect(app).toContain('v-if="!hideShellBreadcrumb"')
  })
})
