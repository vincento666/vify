type PanelRect = {
  left: number
  right: number
  top: number
  bottom: number
}

export type VariableFlyoutPositionInput = {
  triggerRect: PanelRect
  sourcePanelRect: PanelRect | null
  viewportWidth: number
  viewportHeight: number
  flyoutWidth: number
  flyoutMaxHeight: number
  gap: number
  padding: number
  rem: number
  avoidPanelLeft?: number | null
}

export function computeVariableFlyoutPosition(input: VariableFlyoutPositionInput) {
  const anchorRect = input.sourcePanelRect || input.triggerRect
  const rightEdge = anchorRect.right
  const leftEdge = anchorRect.left
  const rightWouldFitViewport = rightEdge + input.gap + input.flyoutWidth <= input.viewportWidth - input.padding
  const rightWouldOverlapPanel = input.avoidPanelLeft
    ? rightEdge + input.gap + input.flyoutWidth > input.avoidPanelLeft - input.gap
    : false
  const placement: 'left' | 'right' = rightWouldFitViewport && !rightWouldOverlapPanel ? 'right' : 'left'
  const left = placement === 'right'
    ? rightEdge + input.gap
    : Math.max(input.padding, leftEdge - input.flyoutWidth - input.gap)
  const maxTop = Math.max(input.padding, input.viewportHeight - input.flyoutMaxHeight - input.padding)
  const top = Math.min(Math.max(input.triggerRect.top - 0.25 * input.rem, input.padding), maxTop)
  return { left, top, placement }
}
