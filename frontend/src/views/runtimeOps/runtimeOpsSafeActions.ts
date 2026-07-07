export type RuntimeOpsSafeAction = 'cancelRun' | 'resumeRun' | 'retryJob' | 'reopenDlq'

const actionText: Record<RuntimeOpsSafeAction, string> = {
  cancelRun: 'cancel run',
  resumeRun: 'resume run',
  retryJob: 'retry job',
  reopenDlq: 'reopen DLQ job',
}

export function buildRuntimeOpsSafeActionConfirmMessage(action: RuntimeOpsSafeAction, targetId: number) {
  return `Confirm ${actionText[action]} #${targetId}?`
}
