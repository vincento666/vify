# Spec 091: Customer Assistant Access-Denied UX

## Goal

Make customer-assistant access denials deterministic for stream endpoints and
persistent in the operator workbench, so embedded demos fail closed instead of
showing a broken stream or a disappearing toast.

## Acceptance Criteria

- Cross-tenant session event streams return a normal `403` envelope before an
  SSE response starts.
- Cross-tenant worker event streams return a normal `403` envelope before an
  SSE response starts.
- Forbidden action/control failures are reflected in the workbench failed-state
  alert, not only in transient notifications.
- Existing local/demo access behavior remains unchanged.

## Non-goals

- Do not redesign the full host permission model.
- Do not add new roles or tenant hierarchy semantics.
- Do not change public SSE payload shapes for authorized streams.

## Evidence

Evidence lives under
`artifacts/slices/091-customer-assistant-access-denied-ux/091.1/`.
