export type ComposerCanvasTab = 'compose' | 'open'
export type ComposerDebugDockTab = 'errors' | 'debug'
export type ComposerSurfaceAction = 'compose' | 'open' | 'publish' | 'debug'

export interface ComposerSurfaceState {
  canvasTab: ComposerCanvasTab
  debugDockOpen: boolean
  debugDockTab: ComposerDebugDockTab
  publishDialogOpen: boolean
  rightPanelOpen: boolean
}

export function composerCanvasTabs() {
  return [
    { key: 'compose' as const, label: '编排' },
    { key: 'open' as const, label: '开放' },
  ]
}

export function resolveComposerSurfaceAction(
  state: ComposerSurfaceState,
  action: ComposerSurfaceAction,
): ComposerSurfaceState {
  if (action === 'open') {
    return {
      ...state,
      canvasTab: 'open',
      publishDialogOpen: false,
      rightPanelOpen: false,
    }
  }

  if (action === 'publish') {
    return {
      ...state,
      canvasTab: 'compose',
      publishDialogOpen: true,
      rightPanelOpen: false,
    }
  }

  if (action === 'debug') {
    return {
      ...state,
      canvasTab: 'compose',
      debugDockOpen: true,
      debugDockTab: 'debug',
      publishDialogOpen: false,
      rightPanelOpen: false,
    }
  }

  return {
    ...state,
    canvasTab: 'compose',
    publishDialogOpen: false,
    rightPanelOpen: false,
  }
}
