# Frontend REM Scale Governance

Hify frontend uses one runtime REM scale contract for visual UI density.

## Runtime Contract

- `installGlobalUiScale()` runs during frontend startup.
- `document.documentElement` receives:
  - `--hify-scale`
  - `--hify-font-scale`
  - `--hify-space-scale`
  - `--hify-control-scale`
  - `--hify-panel-scale`
  - `--hify-root-font-size`
  - `--hify-viewport-width`
- `html` consumes `--hify-root-font-size`, so visual `rem` values scale globally.

Scale points:

- `1280px` viewport -> `14px` root font.
- `1920px` viewport -> `16px` root font.
- `3840px` viewport -> `24px` root font.

## Authoring Rules

- Use design tokens from `frontend/src/styles/tokens.css` where available.
- New visual sizes should use `rem`, not raw `px`.
- Repeated visual sizes should become semantic tokens first.
- Ant Design Vue props such as modal width, drawer size, table column width,
  form label width, and upload trigger sizing should use rem strings where the
  component accepts string dimensions.
- Deferred workflow/chatflow Element Plus props may keep rem strings until the
  workflow/chatflow migration slice is allowed.
- Numeric icon/avatar sizes should become CSS classes with rem sizing.

## Allowed PX

Raw `px` is allowed only when it is not a scalable visual dimension:

- 1px borders, outlines, and crisp hairlines.
- Runtime root font and viewport CSS variable values emitted by `uiScale.ts`.
- Viewport breakpoints in media queries.
- Canvas/graph geometry in script data: coordinates, drag offsets, edge paths,
  DOM measurements, and Vue Flow viewport math.
- Shadows may keep px offsets unless a future visual QA pass decides to govern
  them.

## Gates

- `frontend/src/remScaleClosure.test.ts` blocks unclassified visual `px`.
- Slice evidence lives under
  `artifacts/slices/016-frontend-rem-scale-governance/`.
- Visible frontend changes require browser UAT screenshots and measurements.
