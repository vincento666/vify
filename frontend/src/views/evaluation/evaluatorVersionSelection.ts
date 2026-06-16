export interface EvaluatorVersionOption {
  id: number
  evaluatorId: number
  version: string
}

export type EvaluatorVersionMap = Record<number, EvaluatorVersionOption[]>
export type EvaluatorVersionSelection = Record<number, number>

export function latestEvaluatorVersionSelection(
  evaluatorIds: number[],
  versionsByEvaluator: EvaluatorVersionMap,
): EvaluatorVersionSelection {
  return Object.fromEntries(
    evaluatorIds.map((evaluatorId) => [
      evaluatorId,
      versionsByEvaluator[evaluatorId]?.[0]?.id || 0,
    ]),
  )
}

export function selectedEvaluatorVersionIds(
  evaluatorIds: number[],
  selection: EvaluatorVersionSelection,
): number[] {
  return evaluatorIds
    .map((evaluatorId) => Number(selection[evaluatorId] || 0))
    .filter((versionId) => versionId > 0)
}

export function describeSelectedEvaluatorVersions(
  evaluatorIds: number[],
  selection: EvaluatorVersionSelection,
  versionsByEvaluator: EvaluatorVersionMap,
): string {
  const labels = evaluatorIds
    .map((evaluatorId) => {
      const versionId = Number(selection[evaluatorId] || 0)
      if (!versionId) return ''
      const version = versionsByEvaluator[evaluatorId]?.find((item) => item.id === versionId)
      return version ? `v${version.version}` : ''
    })
    .filter(Boolean)
  return labels.length > 0 ? `评估器版本：${labels.join(', ')}` : '评估器版本：当前草稿'
}
