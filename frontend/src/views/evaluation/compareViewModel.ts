export interface ComparableRunSummary {
  id: number
  experimentId: number
  aggregateScore: number
  failedCases: number
}

export function formatDelta(value: number): string {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${(value * 100).toFixed(1)}%`
}

export function summarizeCaseChangeCount(label: string, count: number): string {
  return `${label} ${count}`
}

export function runOptionLabel(run: ComparableRunSummary): string {
  return `实验 #${run.experimentId} · 运行 #${run.id} · ${(run.aggregateScore * 100).toFixed(1)}% · ${run.failedCases} 失败`
}

export function candidateRunsForBase<T extends ComparableRunSummary>(runs: T[], baseRunId: number): T[] {
  const baseRun = runs.find((run) => run.id === baseRunId)
  if (!baseRun) return []
  return runs.filter((run) => run.id !== baseRunId && run.experimentId === baseRun.experimentId)
}

export function isComparableRunPair(runs: ComparableRunSummary[], baseRunId: number, candidateRunId: number): boolean {
  if (!baseRunId || !candidateRunId || baseRunId === candidateRunId) return false
  const baseRun = runs.find((run) => run.id === baseRunId)
  const candidateRun = runs.find((run) => run.id === candidateRunId)
  return Boolean(baseRun && candidateRun && baseRun.experimentId === candidateRun.experimentId)
}

export function findDefaultRunPair(runs: ComparableRunSummary[]): { baseRunId: number; candidateRunId: number } {
  for (const candidateRun of runs) {
    const baseRun = runs.find((run) => run.id !== candidateRun.id && run.experimentId === candidateRun.experimentId)
    if (baseRun) {
      return { baseRunId: baseRun.id, candidateRunId: candidateRun.id }
    }
  }
  return { baseRunId: 0, candidateRunId: 0 }
}
