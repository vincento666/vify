import { normalizeCaseTags } from './evalSetViewModel'
import type { EvaluatorType } from '@/api/evaluation'

export function describeEvaluatorType(type: EvaluatorType): string {
  if (type === 'EXACT_MATCH') return 'Exact Match'
  if (type === 'LLM_JUDGE') return 'LLM Judge'
  return 'Contains Keywords'
}

export function keywordConfigFromText(text: string) {
  return {
    keywords: normalizeCaseTags(text.split(',')),
    matchMode: 'all',
    ignoreCase: true,
  }
}

export function keywordTextFromConfig(config: Record<string, unknown>): string {
  const keywords = Array.isArray(config.keywords) ? config.keywords : []
  return keywords.map((item) => String(item)).join(', ')
}
