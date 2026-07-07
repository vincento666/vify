import { describe, expect, it } from 'vitest'

import { buildRuntimeOpsSafeActionConfirmMessage } from './runtimeOpsSafeActions'

describe('runtime ops safe actions', () => {
  it('builds explicit confirmation messages for all safe actions', () => {
    expect(buildRuntimeOpsSafeActionConfirmMessage('cancelRun', 701)).toContain('cancel run #701')
    expect(buildRuntimeOpsSafeActionConfirmMessage('resumeRun', 702)).toContain('resume run #702')
    expect(buildRuntimeOpsSafeActionConfirmMessage('retryJob', 910)).toContain('retry job #910')
    expect(buildRuntimeOpsSafeActionConfirmMessage('reopenDlq', 912)).toContain('reopen DLQ job #912')
  })
})
