import { describe, expect, it } from 'vitest'

import { describeEvalSetRelatedExperiment } from './relatedExperimentsViewModel'

describe('relatedExperimentsViewModel', () => {
  it('shows immutable eval set version usage when an experiment binds a version', () => {
    expect(describeEvalSetRelatedExperiment({
      evalSetVersion: '0.0.1',
      status: 'READY',
      latestRunId: null,
    })).toEqual({
      versionText: 'v0.0.1',
      statusTone: 'info',
      runText: '未运行',
    })
  })

  it('falls back to draft/current copy for legacy experiments without version binding', () => {
    expect(describeEvalSetRelatedExperiment({
      evalSetVersion: '',
      status: 'RAN',
      latestRunId: 42,
    })).toEqual({
      versionText: '草稿/当前',
      statusTone: 'success',
      runText: '运行 #42',
    })
  })
})
