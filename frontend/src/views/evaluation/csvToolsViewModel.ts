export function acceptedCsvName(name: string): boolean {
  return name.toLowerCase().endsWith('.csv')
}

export function csvImportHint(): string {
  return 'CSV columns: input, expectedOutput, tags. Use | to separate multiple tags.'
}
