export type CanvasResponsiveLayoutPhase =
  | 'wide'
  | 'right-anchored'
  | 'right-shelved'
  | 'stage-shelved'
  | 'left-rail'
export type CanvasRightPanelMode = 'full' | 'peek'
export type CanvasStageMode = 'fit' | 'clipped' | 'mostly-hidden'
export type CanvasDebugDockMode = 'fluid' | 'locked'

export type CanvasResponsiveLayoutInput = {
  viewportWidth: number
  rem?: number
}

export type CanvasResponsiveLayout = {
  phase: CanvasResponsiveLayoutPhase
  className: string
  rightPanelMode: CanvasRightPanelMode
  stageMode: CanvasStageMode
  debugDockMode: CanvasDebugDockMode
}

const RIGHT_ANCHORED_REM = 90
const RIGHT_SHELVED_REM = 62
const STAGE_SHELVED_REM = 54
const LEFT_RAIL_REM = 46

export function resolveCanvasResponsiveLayout(input: CanvasResponsiveLayoutInput): CanvasResponsiveLayout {
  const rem = Number.isFinite(input.rem) && Number(input.rem) > 0 ? Number(input.rem) : 16
  const viewportRem = Math.max(0, Number(input.viewportWidth || 0)) / rem

  if (viewportRem < LEFT_RAIL_REM) {
    return {
      phase: 'left-rail',
      className: 'canvas-layout-left-rail',
      rightPanelMode: 'peek',
      stageMode: 'mostly-hidden',
      debugDockMode: 'locked',
    }
  }
  if (viewportRem < STAGE_SHELVED_REM) {
    return {
      phase: 'stage-shelved',
      className: 'canvas-layout-stage-shelved',
      rightPanelMode: 'peek',
      stageMode: 'clipped',
      debugDockMode: 'locked',
    }
  }
  if (viewportRem < RIGHT_SHELVED_REM) {
    return {
      phase: 'right-shelved',
      className: 'canvas-layout-right-shelved',
      rightPanelMode: 'peek',
      stageMode: 'fit',
      debugDockMode: 'locked',
    }
  }
  if (viewportRem < RIGHT_ANCHORED_REM) {
    return {
      phase: 'right-anchored',
      className: 'canvas-layout-right-anchored',
      rightPanelMode: 'full',
      stageMode: 'fit',
      debugDockMode: 'locked',
    }
  }
  return {
    phase: 'wide',
    className: 'canvas-layout-wide',
    rightPanelMode: 'full',
    stageMode: 'fit',
    debugDockMode: 'fluid',
  }
}
