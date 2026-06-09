# Plan 026: Workflow/Chatflow Polish Hardening

## Implementation Notes

- Keep implementation scoped to the existing Vue/Element Plus canvas stack.
- Use hify-local class names and tokens while adapting the interaction pattern
  from `vifly-experiment` shared workflow controls.
- Preserve runtime config serialization; UI-only changes must not change backend
  payload shape unless an existing test already covers the migration.
- Prefer focused E2E assertions for layout and visual regressions because the
  defects are user-visible geometry issues.

## Public Interfaces

- Add `lucide-vue-next` to frontend dependencies for lightweight workflow icons.
- Add shared frontend controls for workflow icon buttons and variable selector
  behavior under the existing frontend source tree.
- Keep `/workflows/*` and `/chatflows/*` routes and API envelopes unchanged.
