// @ts-expect-error Vitest runs this source contract in Node; app tsconfig omits node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this source contract in Node; app tsconfig omits node types.
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  // @ts-expect-error Vitest provides process; app tsconfig intentionally omits node types.
  resolve(process.cwd(), 'src/views/aiAssistant/AiAssistantUsageDashboard.vue'),
  'utf8',
)
const shellSource = readFileSync(
  // @ts-expect-error Vitest provides process; app tsconfig intentionally omits node types.
  resolve(process.cwd(), 'src/views/aiAssistant/AiAssistantShell.vue'),
  'utf8',
)

describe('AI Assistant Token/Cost dashboard contract', () => {
  it('contains the complete mainstream usage dashboard surface', () => {
    for (const testId of [
      'ai-assistant-usage-dashboard',
      'ai-assistant-usage-summary',
      'ai-assistant-usage-heatmap',
      'ai-assistant-usage-metric-toggle',
      'ai-assistant-usage-range',
      'ai-assistant-usage-sessions',
      'ai-assistant-usage-session-detail',
      'ai-assistant-usage-providers',
      'ai-assistant-usage-models',
      'ai-assistant-usage-token-types',
      'ai-assistant-usage-loading',
      'ai-assistant-usage-empty',
      'ai-assistant-usage-error',
      'ai-assistant-usage-unknown-cost',
    ]) {
      expect(source).toContain(`data-testid="${testId}"`)
    }
    for (const label of ['今天', '昨天', '30 天', '累计', 'Token', 'Cost', '价格未知']) {
      expect(source).toContain(label)
    }
  })

  it('loads every aggregate and exposes session drilldown without scope selectors', () => {
    for (const call of [
      'getAiAssistantUsageSummary',
      'getAiAssistantUsageDaily',
      'getAiAssistantUsageSessions',
      'getAiAssistantUsageDimensions',
      'getAiAssistantUsageSession',
    ]) {
      expect(source).toContain(call)
    }
    expect(source).not.toContain('userId')
    expect(source).not.toContain('workspaceId')
  })

  it('is reachable from the AI Assistant Token usage detail action', () => {
    expect(shellSource).toContain('data-testid="ai-assistant-usage-entry"')
    expect(shellSource).toContain('to="/ai-assistant/usage"')
    expect(shellSource).toContain('Token 用量')
  })
})
