# Spec 027: Workflow/Chatflow Config Hardening

## Goal

Close the remaining Workflow/Chatflow authoring defects that break Coze-like
configuration fidelity: Start defaults must be locked runtime inputs, variable
reference controls must be compact and inline-triggered, model/resource
selectors must be true overlays, condition branches must support variable
references and default values, and icon buttons must be visually consistent.

## Slices

1. **027.1 Start defaults and trial input**: system/default Start inputs are
   locked, not required, not deletable, and do not appear as extra trial-run
   fields; only user-created Start inputs are editable/removable and may be
   supplied during trial runs.
2. **027.2 Variable reference controls**: replace remaining legacy variable
   buttons and reference affordances with the compact selector.
3. **027.3 Floating selectors**: model and dropdown pickers render as overlays
   that do not reflow the config panel.
4. **027.4 Selector branch conditions**: condition/selector branches support
   variable references, default values, and Coze-like condition row layout from
   schema through runtime execution.
5. **027.5 Icon button polish**: align all non-primary icon buttons to the
   lightweight bordered/background style.

## Acceptance Gates

Every slice must save RED, unit, E2E, rem, build/UAT evidence under
`artifacts/slices/027-workflow-chatflow-config-hardening/{slice}/`.
