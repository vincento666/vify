export interface EvalSetCardInput {
  caseCount: number
}

export interface EvalSetCardDescription {
  caseCountText: string
  tone: 'empty' | 'ready'
}

export function describeEvalSetCard(evalSet: EvalSetCardInput): EvalSetCardDescription {
  return {
    caseCountText: `${evalSet.caseCount} 条用例`,
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

export function displayEvalSetFieldLabel(field: { key: string; label: string }): string {
  if (field.key === 'input') return '输入'
  if (field.key === 'expectedOutput') return '期望输出'
  return field.label
}

export interface EvalSetVersionStateInput {
  latestVersion?: string
  draftChanged?: boolean
}

export interface EvalSetVersionStateDescription {
  label: string
  tone: 'draft' | 'dirty' | 'version'
  submitDisabled: boolean
}

export function describeEvalSetVersionState(evalSet: EvalSetVersionStateInput): EvalSetVersionStateDescription {
  const latestVersion = String(evalSet.latestVersion || '')
  if (!latestVersion) {
    return { label: '草稿', tone: 'draft', submitDisabled: false }
  }
  if (evalSet.draftChanged) {
    return { label: `v${latestVersion} 后有草稿变更`, tone: 'dirty', submitDisabled: false }
  }
  return { label: `v${latestVersion}`, tone: 'version', submitDisabled: true }
}

export interface EvalSetFieldDraft {
  key: string
  label: string
  contentType: string
  required: boolean
  displayOrder: number
}

export function normalizeFieldDrafts(fields: EvalSetFieldDraft[]): EvalSetFieldDraft[] {
  return fields
    .map((field, index) => ({
      key: field.key.trim(),
      label: field.label.trim() || field.key.trim(),
      contentType: (field.contentType || 'TEXT').trim().toUpperCase(),
      required: Boolean(field.required),
      displayOrder: index + 1,
    }))
    .filter((field) => field.key && field.label)
}
