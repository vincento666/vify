export interface ObserveMetrics {
  runCount?: number
  handoffCount?: number
  handoffRate?: number
  channelDistribution?: Record<string, number>
  channelDeliveryFailures?: number
}

export interface ObserveMetricTile {
  label: string
  value: string
}

export function buildObserveMetricTiles(metrics: ObserveMetrics): ObserveMetricTile[] {
  const channels = Object.entries(metrics.channelDistribution || {}).sort((left, right) => right[1] - left[1])
  const topChannel = channels[0]
  return [
    { label: 'Runs', value: String(metrics.runCount || 0) },
    { label: 'Handoffs', value: String(metrics.handoffCount || 0) },
    { label: 'Handoff Rate', value: `${((metrics.handoffRate || 0) * 100).toFixed(1)}%` },
    { label: 'Top Channel', value: topChannel ? `${topChannel[0]} ${topChannel[1]}` : '-' },
    { label: 'Channel Failures', value: String(metrics.channelDeliveryFailures || 0) },
  ]
}

export function normalizeObserveRunIdQuery(value: string | string[] | undefined): number {
  const raw = Array.isArray(value) ? value[0] : value
  const runId = Number(raw || 0)
  return Number.isInteger(runId) && runId > 0 ? runId : 0
}
