export function formatDelta(value: number): string {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${(value * 100).toFixed(1)}%`
}

export function summarizeCaseChangeCount(label: string, count: number): string {
  return `${label} ${count}`
}
