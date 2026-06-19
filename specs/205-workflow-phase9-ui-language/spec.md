# Spec 205: Workflow Phase 9 UI Language

## Goal

Remove engineering runtime terminology from the default workflow/chatflow UI
surfaces while preserving debug affordances.

This addresses the Phase 9 requirement that business users see status, result,
and debug entry points without worker/runtime/checkpoint internals in the main
product surface.

## In Scope

- Replace raw checkpoint/event identifiers in the waiting summary copy.
- Rename version runtime test copy to product-facing realtime test language.
- Hide debug refs from the published-version result summary.
- Keep debug tools and underlying Runtime v2 API calls intact.

## Out of Scope

- Debug dock redesign.
- Customer assistant UI.
- Removing runtime refs from backend API contracts.

## Acceptance Criteria

- The waiting summary card does not show `Checkpoint #` or `Event #`.
- Published-version test controls do not show `Runtime v2` or `debugRef` in the
  user-facing source copy.
- Existing version test controls remain wired to the Runtime v2 gateway.
