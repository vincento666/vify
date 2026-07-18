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
    expect(content).toContain('ai-assistant-shell-result')
    expect(content).toContain('ai-assistant-shell-result-output')
    expect(content).toContain('ai-assistant-shell-result-copy')
    expect(content).toContain('expected command as shell fold header')
    expect(content).toContain('expected shell fold header to avoid nested tool labels')
    expect(content).toContain('expected shell fold header to show one status only')
    expect(content).toContain('expected shell fold header to omit inner status icons')
    expect(content).toContain('code-save-test-uat.json')
    expect(content).toContain('code-save-test-completed.png')
  })
})

describe('AI Assistant light activity shell UAT script', () => {
  const content = readFrontendFile('e2e/ai-assistant-activity-shell-uat.mjs')

  it('covers stable folding, live text, approval, error and durable child presence', () => {
    expect(content).toContain('ai-assistant-activity-feed')
    expect(content).toContain('ai-assistant-activity-toggle')
    expect(content).toContain('ai-assistant-subagent-presence')
    expect(content).toContain('我先核对运行时配置，并同步检查权限记录。')
    expect(content).toContain('running activity should default expanded')
    expect(content).toContain('completed activity should auto collapse')
    expect(content).toContain('approval activity should stay expanded')
    expect(content).toContain('failed activity should stay expanded')
    expect(content).toContain('manual override should survive stable activity SSE upsert and snapshot refresh')
    expect(content).toContain('running subagent should show presence details')
    expect(content).toContain('completed subagent should collapse')
    expect(content).toContain("reducedMotion: 'reduce'")
    expect(content).toContain('ai-assistant-light-activity-shell.png')
    expect(content).toContain('ai-assistant-approval-error-states.png')
  })
})
