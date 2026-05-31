export interface EvalSetCardInput {
  caseCount: number
}

export interface EvalSetCardDescription {
  caseCountText: string
  tone: 'empty' | 'ready'
}

export function describeEvalSetCard(evalSet: EvalSetCardInput): EvalSetCardDescription {
  return {
    caseCountText: `${evalSet.caseCount} cases`,
    tone: evalSet.caseCount > 0 ? 'ready' : 'empty',
  }
}

export function normalizeCaseTags(tags: string[]): string[] {
  const normalized: string[] = []
  for (const tag of tags) {
    const value = tag.trim()
    if (value && !normalized.includes(value)) {
      normalized.push(value)
    }
  }
  return normalized
}
