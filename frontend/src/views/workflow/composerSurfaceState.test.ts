import { describe, expect, it } from 'vitest'

import {
  composerCanvasTabs,
  resolveComposerSurfaceAction,
  type ComposerSurfaceState,
} from './composerSurfaceState'

describe('composer surface state', () => {
  const baseState: ComposerSurfaceState = {
    canvasTab: 'compose',
    debugDockOpen: false,
    debugDockTab: 'errors',
    publishDialogOpen: false,
    rightPanelOpen: false,
  }

  it('exposes only compose and open lifecycle tabs until statistics has a real product surface', () => {
    expect(composerCanvasTabs().map((tab) => tab.key)).toEqual(['compose', 'open'])
    expect(composerCanvasTabs().map((tab) => tab.label)).toEqual(['编排', '开放'])
  })

  it('opens the center Open surface without activating a right-side ops panel', () => {
    expect(resolveComposerSurfaceAction(baseState, 'open')).toEqual({
      canvasTab: 'open',
      debugDockOpen: false,
      debugDockTab: 'errors',
      publishDialogOpen: false,
      rightPanelOpen: false,
    })
  })

  it('opens publish as a modal and keeps run debugging out of publish state', () => {
    expect(resolveComposerSurfaceAction(baseState, 'publish')).toEqual({
      canvasTab: 'compose',
      debugDockOpen: false,
      debugDockTab: 'errors',
      publishDialogOpen: true,
      rightPanelOpen: false,
    })
  })

  it('opens run debug in the bottom dock without activating a statistics surface', () => {
    expect(resolveComposerSurfaceAction(baseState, 'debug')).toEqual({
      canvasTab: 'compose',
      debugDockOpen: true,
      debugDockTab: 'debug',
      publishDialogOpen: false,
      rightPanelOpen: false,
    })
  })
})
