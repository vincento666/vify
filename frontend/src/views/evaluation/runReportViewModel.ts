export function filterCaseResults<T extends { status: string }>(cases: T[], status: string): T[] {
  if (!status || status === 'ALL') return cases
  return cases.filter((item) => item.status === status)
}

export function failureInvestigationTitle(failedCases: number): string {
  return `${failedCases} failed cases need investigation`
}

export function rerunActionLabel(caseResult: { status: string }): string {
  return caseResult.status === 'FAILED' ? '重跑失败用例' : '重跑用例'
}
