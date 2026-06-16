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

describe('HifyFormDialog Ant Design Vue migration', () => {
  it('renders with Ant Design Vue modal/form primitives and no Element Plus contract', () => {
    const content = readProjectFile('src/components/base/HifyFormDialog.vue')

    expect(content).not.toMatch(/element-plus/)
    expect(content).not.toMatch(/<el-/)
    expect(content).toMatch(/<a-modal/)
    expect(content).toMatch(/v-model:open="visible"/)
    expect(content).toMatch(/<a-form/)
    expect(content).toMatch(/<a-button/)
  })
})
