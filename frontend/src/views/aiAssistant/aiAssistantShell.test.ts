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

describe('AI Assistant shell UI contract', () => {
  const content = readProjectFile('src/views/aiAssistant/AiAssistantShell.vue')

  it('renders conversation timeline composer and execution echo regions', () => {
    for (const testId of [
      'ai-assistant-shell',
      'ai-assistant-conversation-window',
      'ai-assistant-event-stream',
      'ai-assistant-event-card',
      'ai-assistant-composer',
      'ai-assistant-send',
    ]) {
      expect(content).toContain(`data-testid="${testId}"`)
    }
    expect(content).toContain('buildAiAssistantTimeline')
    expect(content).toContain('streamPulse')
    expect(content).not.toContain('chain-of-thought')
  })
})
