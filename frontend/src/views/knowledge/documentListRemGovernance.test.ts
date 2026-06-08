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

describe('document list rem governance', () => {
  it('keeps document list visual sizing on rem tokens', () => {
    const content = readProjectFile('src/views/knowledge/DocumentList.vue')
    const rawVisualPxPattern = /\b(?:font-size|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|min-width|max-width|min-height|max-height|width|height|border-radius)\s*:\s*(?!1px\b)[^;\n]*\bpx\b/g
    const templatePxPattern = /(?:width|label-width)="[0-9.]+px"|:width="[0-9.]+\"|:size="[0-9.]+\"|style="[^"]*[0-9.]+px|height:\s*'[0-9.]+px'/g

    const matches = [
      ...collectMatches(content, rawVisualPxPattern),
      ...collectMatches(content, templatePxPattern),
    ]

    expect(matches).toEqual([])
  })

  it('exposes business retrieval strategy controls without mock-only wording', () => {
    const content = readProjectFile('src/views/knowledge/DocumentList.vue')

    expect(content).toContain('检索方式')
    expect(content).toContain('智能推荐')
    expect(content).toContain('高级设置')
    expect(content).not.toContain('当前为 Mock 模式')
    expect(content).not.toContain('tokens')
    expect(content).not.toContain('召回')
  })

  it('keeps knowledge detail table markup and action columns stable', () => {
    const content = readProjectFile('src/views/knowledge/DocumentList.vue')

    expect(content).not.toContain('</el-form-item>\n        </el-form-item>')
    expect(content).not.toContain('</el-tab-pane>\n        </el-tab-pane>')
    expect(content.match(/function statusType/g)).toHaveLength(1)
    expect(content).not.toContain('label="操作" width="8.75rem" fixed="right"')
    expect(content).toContain('document-action-cell')
    expect(content).toContain('faq-action-cell')
    expect(content).toContain('retrieval-topk-input')
    expect(content).toContain('retrieval-advanced-button')
    expect(content).toContain('retrieval-search-button')
    expect(content).toContain('grid-template-columns: minmax(18rem, 1fr) 12rem 9rem 7.5rem 8.5rem')
  })
})
