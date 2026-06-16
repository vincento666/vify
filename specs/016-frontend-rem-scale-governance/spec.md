# Spec 016: Frontend REM Scale Governance

## Goal

Make Hify frontend use one global REM-based visual scale contract, modeled after
`vifly-experiment`, so UI density stays coherent across desktop widths and can
be tuned from one root scale source.

This spec does not change backend APIs, response envelopes, routes, persisted
data, or product behavior. It changes frontend visual sizing governance.

## Current Gap

Hify currently has design tokens and Element Plus variable overrides, but the
values are fixed `px`. `html` is fixed at `14px`, source styles contain no
numeric `rem`, and major pages have many direct visual `px` declarations and
template inline sizes. Changing root font size today cannot scale the UI
coherently.

`vifly-experiment` already has the target shape:

- runtime scale state computed from viewport width;
- root CSS variable such as `--vf-root-font-size`;
- `html { font-size: var(--vf-root-font-size); }`;
- REM visual tokens;
- governance tests that block raw visual `px` from critical surfaces;
- geometry whitelist so canvas coordinates, hit areas, DOM measurements, and
  drag offsets are not blindly remified.

Hify needs the same pattern adapted to its Vue + Element Plus + Vue Flow stack.

## Product Boundary

- Scope is PC/desktop visual scaling first. Existing mobile responsive behavior
  must not regress, but this spec does not promise mobile-first redesign.
- Visual dimensions should be controlled by Hify REM tokens.
- Runtime geometry dimensions may remain `px` when they represent coordinates,
  measurements, drag offsets, hit areas, or third-party canvas math.
- Element Plus stays in use. Hify should map Element Plus CSS variables to REM
  tokens where practical.
- Vue Flow canvas graph coordinates stay numeric/px-like data and must not be
  converted to REM.

## User Value

Product users see Hify as one coherent app instead of different pages feeling
too large, too small, or mismatched after display-size changes. Developers gain
one scale contract for future frontend work.

## Requirements

- **FR-001**: Frontend MUST expose a global desktop UI scale state on
  `document.documentElement`.
- **FR-002**: `html` font size MUST be driven by a CSS variable, not fixed `px`.
- **FR-003**: Scale state MUST include root font size, viewport width, and
  compatibility scale variables for visual/font/space/control/panel categories.
- **FR-004**: Visual tokens for font sizes, spacing, radius, layout chrome, card
  padding, controls, dialogs, drawers, and common page shells MUST be expressed
  in `rem`.
- **FR-005**: Element Plus variable overrides SHOULD consume Hify REM tokens for
  major visual dimensions: font sizes, component sizes, radius, card padding,
  dialog width, table row density, form label width, and popper/control padding
  where exposed by CSS variables.
- **FR-006**: Critical app chrome and page surfaces MUST migrate away from raw
  visual `px`: app shell, base table/dialog components, provider, agent,
  knowledge, chat, MCP, workflow list, workflow/chatflow canvas, evaluation, and
  agent workbench.
- **FR-007**: Workflow and chatflow canvas geometry MUST keep coordinate,
  measurement, drag, edge path, handle hit area, and viewport math in explicit
  geometry units or variables; these are not visual rem tokens.
- **FR-008**: Template inline visual sizes such as `width="520px"`,
  `label-width="90px"`, `style="margin-left:8px"`, and numeric visual icon sizes
  SHOULD be replaced by tokenized props/classes/styles unless they are geometry
  whitelist cases.
- **FR-009**: Governance tests MUST block regressions for the scale contract and
  critical raw visual `px` usage.
- **FR-010**: Browser UAT MUST verify multiple desktop widths and at least one
  compact width for visible app routes.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 016.1 Scale foundation | App root publishes continuous desktop scale vars; `html` consumes root font size; base tokens are REM | RED: scale contract tests fail; Unit: scale utility and CSS contract; Build: frontend build; UAT: root vars visible in browser |
| 016.2 Shared shell and Element Plus bridge | App shell, base table/dialog, global styles, and Element Plus overrides consume REM tokens | RED: shell/token governance tests fail; Unit: governance tests; E2E: app chrome opens; UAT: sidebar/topbar/table/dialog scale at desktop widths |
| 016.3 Management pages | Provider, Agent list, Knowledge, MCP, Workflow list, Chatflow list, Evaluation panels migrate visual `px` to REM tokens | RED: page governance tests fail; Unit: page tests; E2E: route smoke; UAT: representative CRUD/list pages |
| 016.4 Workflow and Chatflow canvas | Canvas visual chrome remified while geometry whitelist remains explicit and tested | RED: canvas geometry/visual tests fail; Unit: workflow tests; E2E: node add/config/debug path; UAT: desktop widths and drag/click sanity |
| 016.5 Agent Workbench and Chat | Agent workbench and chat panel visual sizes consume REM tokens and preview/chat flows remain usable | RED: workbench/chat governance tests fail; Unit: existing workbench/chat helpers; E2E: preview/chat smoke; UAT: workbench and chat screenshots |
| 016.6 Governance closure | Remaining raw visual `px` either migrated or explicitly allowlisted; docs and evidence complete | RED: all-source governance test fails until allowlist/migration complete; Unit/build/e2e/browser UAT all green; Docs evidence updated |

## Acceptance Gates

Every slice must keep evidence under:

```text
artifacts/slices/016-frontend-rem-scale-governance/{slice-id}/
├── red.txt
├── unit.txt
├── build.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

For slices affecting visible UI, Browser UAT must include real browser
verification. At minimum, final closure covers widths `1280`, `1440`, `1920`,
`2560`, and compact `900`.

## Non-Scope

- No backend schema/API changes.
- No mobile redesign.
- No replacing Element Plus.
- No converting Vue Flow graph coordinates to REM.
- No one-shot unreviewed global regex rewrite.
