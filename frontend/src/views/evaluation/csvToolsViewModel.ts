export function acceptedCsvName(name: string): boolean {
  return name.toLowerCase().endsWith('.csv')
}

export function csvImportHint(): string {
  return 'CSV 列：input、expectedOutput、tags。多个标签使用 | 分隔。'
}
