// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readFrontendFile(path: string) {
  return readFileSync(resolve(frontendRoot, path), 'utf8')
}

describe('AI Assistant code-save-test pressure UAT script', () => {
  const content = readFrontendFile('e2e/ai-assistant-code-save-test-uat.mjs')

  it('drives a code writing save readback and test execution attempt journey', () => {
    expect(content).toContain('tmp/ai-assistant-code-save-test-uat.mjs')
    expect(content).toContain('write_workspace_file')
    expect(content).toContain('read_workspace_file')
    expect(content).toContain('run_shell')
    expect(content).toContain('完全访问权限')
    expect(content).toContain('expected controlled shell run to complete')
    expect(content).toContain('PASS ai-assistant-code-save-test-uat')
    expect(content).toContain('ai-assistant-run-final-answer')
    expect(content).toContain('code-save-test-uat.json')
    expect(content).toContain('code-save-test-completed.png')
  })
})
