import type {
  AiAssistantUsageCostState,
  AiAssistantUsageDaily,
} from '@/api/aiAssistant'

export type UsageMetric = 'tokens' | 'cost'

export interface UsageHeatmapCell {
  date: string
  totalTokens: number
  costUsd: string | null
  costState: AiAssistantUsageCostState
  intensity: number
  unknownCost: boolean
}

function localIsoDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addLocalDays(value: Date, days: number): Date {
  const result = new Date(value)
  result.setDate(result.getDate() + days)
  return result
}

export function usageDateRange(today = new Date()) {
  return {
    detailFrom: localIsoDate(addLocalDays(today, -29)),
    heatmapFrom: localIsoDate(addLocalDays(today, -364)),
    to: localIsoDate(today),
  }
}

export function formatTokenCount(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) {
    const compact = value / 1_000
    return `${Number.isInteger(compact) ? compact.toFixed(0) : compact.toFixed(1)}k`
  }
  return String(value)
}

export function formatOptionalTokenCount(value: number | null): string {
  return value === null ? 'Token 未知' : formatTokenCount(value)
}

export function formatCostState(value: {
  costUsd: string | null
  costState: AiAssistantUsageCostState
  unknownCostCount: number
}): string {
  if (value.costState === 'unknown' || value.costUsd === null) return '价格未知'
  const amount = Number(value.costUsd)
  const rendered = amount > 0 && amount < 0.0001
    ? '<$0.0001'
    : `$${amount < 0.01 ? amount.toFixed(4) : amount.toFixed(2)}`
  return value.costState === 'partial' ? `${rendered} + 未知` : rendered
}

export function formatCallCost(value: string | null): string {
  return value === null
    ? '价格未知'
    : formatCostState({ costUsd: value, costState: 'complete', unknownCostCount: 0 })
}

export function parseUsageUtcDateTime(value: string): Date {
  const hasOffset = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
  return new Date(hasOffset ? value : `${value}Z`)
}

export function buildUsageHeatmap(
  rows: Array<Pick<AiAssistantUsageDaily, 'date' | 'totalTokens' | 'costUsd' | 'costState'>>,
  from: string,
  to: string,
  metric: UsageMetric,
): UsageHeatmapCell[] {
  const byDate = new Map(rows.map((row) => [row.date, row]))
  const cursor = new Date(`${from}T12:00:00`)
  const last = new Date(`${to}T12:00:00`)
  const values: Array<Omit<UsageHeatmapCell, 'intensity'>> = []
  while (cursor <= last) {
    const date = localIsoDate(cursor)
    const row = byDate.get(date)
    values.push({
      date,
      totalTokens: row?.totalTokens || 0,
      costUsd: row?.costUsd ?? null,
      costState: row?.costState || 'complete',
      unknownCost: metric === 'cost' && row?.costState === 'unknown',
    })
    cursor.setDate(cursor.getDate() + 1)
  }
  const numeric = values.map((row) =>
    metric === 'tokens' ? row.totalTokens : row.costUsd === null ? 0 : Number(row.costUsd),
  )
  const maximum = Math.max(0, ...numeric)
  return values.map((row, index) => ({
    ...row,
    intensity: maximum <= 0 || numeric[index] <= 0 ? 0 : Math.max(1, Math.ceil((numeric[index] / maximum) * 5)),
  }))
}
