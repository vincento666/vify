export function filterCaseResults<T extends { status: string }>(cases: T[], status: string): T[] {
  if (!status || status === 'ALL') return cases
  return cases.filter((item) => item.status === status)
}

export function failureInvestigationTitle(failedCases: number): string {
  return `${failedCases} 个失败用例需要排查`
}

export function rerunActionLabel(caseResult: { status: string }): string {
  return caseResult.status === 'FAILED' ? '重跑失败用例' : '重跑用例'
}

export function targetEvidenceActionLabel(caseResult: { targetType?: string; targetDebugUrl?: string }): string {
  if (!caseResult.targetDebugUrl) return ''
  if (caseResult.targetType === 'WORKFLOW') return '查看 Workflow 调试'
  if (caseResult.targetType === 'CHATFLOW') return '查看 Chatflow 调试'
  return ''
}

export function targetEvidenceHref(caseResult: { targetDebugUrl?: string }): string {
  return caseResult.targetDebugUrl || ''
}
