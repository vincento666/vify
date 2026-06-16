# Plan 016: Frontend REM Scale Governance

## Approach

Use vertical TDD slices. Start with a small public scale contract, then move
visual surfaces behind that contract. Do not bulk-convert every `px` at once.

Public frontend contract:

- `frontend/src/utils/uiScale.ts`
  - `createUiScaleSnapshot(width, config?)`
  - `toUiScaleCssVariables(snapshot)`
  - `applyUiScaleToElement(element, width, config?)`
  - `classifyScaleDimension(context)` and geometry whitelist helpers
- `frontend/src/composables/useUiScale.ts`
  - `installGlobalUiScale(target?)`
  - `useUiScale(target?)`
- `frontend/src/styles/tokens.css`
  - `--hify-root-font-size`
  - `--hify-scale`
  - REM font/space/radius/layout/control tokens
- `frontend/src/styles/global.css`
  - `html { font-size: var(--hify-root-font-size); }`

Compatibility variables mirror `vifly-experiment` names in Hify naming:

- `--hify-scale`
- `--hify-font-scale`
- `--hify-space-scale`
- `--hify-control-scale`
- `--hify-panel-scale`
- `--hify-root-font-size`
- `--hify-viewport-width`

## Scale Algorithm

Adapt `vifly-experiment` continuous desktop interpolation:

- min width: `1280`
- base width: `1920`
- max width: `3840`
- visual scale: `0.875` at min, `1` at base, `1.5` at max
- base root font size: `16px`
- root font size = `baseRootFontSize * visualScale`

This lets page-level REM sizes scale by changing the root font size. Category
scale vars stay as compatibility/debug mirrors and future escape hatches.

## Token Migration Rules

- Visual dimension -> REM token.
- Repeated visual literal -> semantic token first.
- One-off low-risk visual literal -> direct `rem` acceptable during migration,
  but prefer token for shared surfaces.
- Border hairlines may stay `1px` where physical crispness matters.
- Shadows may keep px offsets initially unless they are part of a governed
  critical surface.
- Geometry and measurements keep px with explicit naming or allowlist.

## Geometry Whitelist

Allowed `px` contexts:

- canvas coordinates and node positions;
- edge path control points;
- Vue Flow viewport/zoom math;
- DOM `getBoundingClientRect` measurements;
- drag offsets and pointer positions;
- handle hit area calibration;
- screenshot/e2e viewport dimensions;
- third-party library prop contracts requiring pixels.

## Test Strategy

TDD order per slice:

1. Add one behavior/governance test.
2. Capture RED output in slice artifact.
3. Implement minimum code.
4. Run focused unit test.
5. Run build.
6. Run focused e2e/browser UAT when UI visible.
7. Update task status and evidence.

Behavior tests should assert public contract:

- computed scale vars at known widths;
- `html` root font size bound to Hify var;
- tokens use `rem`;
- governance rejects raw visual `px` in chosen critical files;
- canvas geometry allowlist stays explicit.

## Rollout

Current status:

- 016.1 complete: global scale contract, root font-size, base tokens.
- 016.2 complete: app shell, base table/dialog, Element Plus bridge.
- 016.3 complete for provider, agent list, knowledge list/document list, MCP
  list, workflow/chatflow list, and evaluation panels.
- 016.4 complete: workflow/chatflow canvas visual chrome, with graph geometry
  kept as explicit numeric coordinates.
- 016.5 complete: agent workbench and chat visual layout.
- 016.6 complete: all-source governance closure, final unit/build/e2e/browser
  UAT, and authoring docs.

### Slice 016.1

Add scale utility/composable, connect app startup, convert base tokens enough to
prove root scaling. Keep page migration minimal.

### Slice 016.2

Convert app shell, base components, global utility classes, Element Plus bridge.

### Slice 016.3

Convert management/list/detail surfaces by module. Prefer shared base class/token
changes where they reduce page-specific edits.

### Slice 016.4

Convert workflow/chatflow visual chrome. Preserve Vue Flow graph geometry.
Add allowlist tests for geometry `px`.

### Slice 016.5

Convert Agent Workbench and Chat. Preserve preview/chat behavior.

### Slice 016.6

All-source governance closure. Remaining `px` must be allowed, documented, or
migrated.

## Browser UAT Routes

Final UAT route set:

- `/provider`
- `/agent`
- `/agents/new`
- `/chat`
- `/knowledge`
- `/workflows`
- `/workflows/create`
- `/chatflows/create`
- `/evaluation`
- `/mcp`

Widths:

- `900`
- `1280`
- `1440`
- `1920`
- `2560`

Checks:

- root vars present;
- no blank screen;
- no horizontal overflow except known canvas/workbench scroll surfaces;
- sidebar/topbar proportional;
- Element Plus controls visible and clickable;
- workflow canvas nodes and panels still clickable.

## Risk Controls

- Keep user dirty work untouched.
- Prefer shared tokens over broad per-file churn.
- Do not refactor product logic while visual tests are red.
- Never migrate graph coordinates by regex.
- Browser screenshots required before final closure.
