export interface RelatedExperimentViewInput {
  evalSetVersion?: string
  status: string
  latestRunId: number | null
}

export interface RelatedExperimentViewDescription {
  versionText: string
  statusTone: 'success' | 'warning' | 'info'
  runText: string
}

export function describeEvalSetRelatedExperiment(input: RelatedExperimentViewInput): RelatedExperimentViewDescription {
  const version = String(input.evalSetVersion || '').trim()
  return {
    versionText: version ? `v${version}` : '草稿/当前',
    statusTone: input.status === 'RAN' ? 'success' : input.status === 'FAILED' ? 'warning' : 'info',
    runText: input.latestRunId ? `运行 #${input.latestRunId}` : '未运行',
  }
}
