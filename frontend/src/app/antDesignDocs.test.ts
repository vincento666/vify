// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { existsSync, readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readRepoFile(path: string) {
  return readFileSync(resolve(repoRoot, path), 'utf8')
}

describe('Ant Design Vue migration docs', () => {
  it('documents direct Ant usage and the single app install seam', () => {
    const path = 'docs/frontend-ant-design-vue-platform.md'
    expect(existsSync(resolve(repoRoot, path))).toBe(true)

    const docs = readRepoFile(path)
    expect(docs).toContain('frontend/src/app/ant-design.ts')
    expect(docs).toContain('installAntDesign')
    expect(docs).toContain('directly')
    expect(docs).toContain('shared/ui')
  })

  it('documents integration packaging dependencies and deferred workflow scope', () => {
    const path = 'docs/frontend-integration-packaging.md'
    expect(existsSync(resolve(repoRoot, path))).toBe(true)

    const docs = readRepoFile(path)
    expect(docs).toContain('ant-design-vue')
    expect(docs).toContain('@ant-design/icons-vue')
    expect(docs).toContain('workflow/chatflow')
    expect(docs).toContain('Element Plus')
  })
})
