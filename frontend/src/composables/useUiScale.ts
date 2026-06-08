import { onMounted, onUnmounted } from 'vue'

import { applyUiScaleToElement } from '@/utils/uiScale'

export function installGlobalUiScale(
  target: HTMLElement | null = typeof document !== 'undefined' ? document.documentElement : null,
) {
  if (!target || typeof window === 'undefined') {
    return {
      sync: () => null,
      dispose: () => undefined,
    }
  }

  const sync = () => applyUiScaleToElement(target, window.innerWidth)

  sync()
  window.addEventListener('resize', sync, { passive: true })

  return {
    sync,
    dispose: () => window.removeEventListener('resize', sync),
  }
}

export function useUiScale(
  target: HTMLElement | null = typeof document !== 'undefined' ? document.documentElement : null,
) {
  let controller: ReturnType<typeof installGlobalUiScale> | null = null

  onMounted(() => {
    controller = installGlobalUiScale(target)
  })

  onUnmounted(() => {
    controller?.dispose()
  })

  return {
    sync: () => controller?.sync(),
  }
}
