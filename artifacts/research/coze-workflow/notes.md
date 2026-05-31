# Coze Workflow Canvas Reference Notes

## Browser Access

- Direct Coze platform access: `https://www.coze.com/`
- Evidence: `coze-home-1440.png`
- Result: page reached through Chromium, but the first unauthenticated capture stayed in a loading state.

## Current In-App Browser Visual References

- Current source URL opened by the user in Codex in-app Browser: `https://www.coze.cn/work_flow?workflow_id=7639360865686634515&space_id=7392442439686553619`
- Full desktop evidence: `in-app-coze-chatflow-canvas-current.png`
- Cropped browser-pane evidence: `in-app-coze-chatflow-canvas-pane.png`
- Node config panel evidence: `in-app-coze-node-config-0113.png`
- This current authenticated `coze.cn` canvas is the implementation reference for spec 011/012 visual work.

## Historical Public Visual References

- Source page archived locally: `chloevolution-coze-workflow.html`
- Key canvas image: `coze-workflow-node_hu_503fa31c1fa4b206.png`
- Additional interaction references:
  - `google-web-search-plugin_hu_25e5901901364e44.png`
  - `google-web-search-plugin-settings_hu_155521dcc67dc565.png`
  - `run-test-result-example_hu_a4136a4cf9c7fee8.png`
  - `code-node-settings_hu_c0189fbcd6f83c96.png`
  - `llm-node-settings_hu_eb64901f44dbc0a8.png`

The public article screenshots are historical and must not be used as the pixel target when they conflict with the current in-app Coze canvas.

## UI Observations To Reuse

- Header shows back navigation, app icon, flow name, status badge such as `已自动保存`, and a light workspace strip.
- Canvas uses a subtle dotted grid with white rounded node cards and small purple side ports.
- Current default chatflow graph shows compact `开始`, intermediate operation node, and `结束` cards; `结束` can sit partly outside the visible right edge.
- Node cards are flatter than the historical screenshots: icon + title header, compact input/output rows, and pill variables.
- Clicking a node selects it with a purple outline and opens a right-side configuration panel with collapsible sections such as input, code/model body, output, and error/exception handling.
- Bottom toolbar is centered near the lower edge with zoom and tool icons.
- Node creation is exposed through a prominent bottom-right `+ 添加节点` button and a floating vertical node palette.

## Implementation Boundary

- Spec 011.1 only establishes module tabs and route shell.
- Spec 011.2 starts the canvas replica using `in-app-coze-chatflow-canvas-pane.png` as the primary visual target.
