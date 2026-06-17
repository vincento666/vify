# Feature Spec: Customer Assistant Session Inbox Dashboard MVP

## Status

Slice 121.1 complete.

## User Story

As a customer-assistant operator, I can see seeded MVP customer sessions as an inbox/dashboard with session status, task/action counts, last activity hints, and can open a session directly without hunting through demo story cards.

## Functional Requirements

- Render a session inbox in the operator workbench area, outside the customer conversation lane.
- The inbox must list seeded demo sessions with:
  - session id;
  - customer name;
  - story title;
  - status hint for active, pending, blocked, or completed work;
  - task count;
  - pending action count;
  - last activity derived from seeded metrics.
- Selecting an inbox row must load the same workbench session/story as the existing seeded demo story loader.
- The selected row must visibly reflect the active session.
- The inbox must fit desktop and narrow browser viewports without horizontal overflow.
- Use existing `/api/v1/customer-assistant/demo-stories` and `/api/v1/customer-assistant/demo-stories/metrics` data unless RED proves a backend gap.

## Non-Goals

- New backend session search, assignment, or omnichannel inbox APIs.
- Real-time cross-session streaming.
- Bulk assignment, SLA timers, filters, or archive management beyond MVP visibility hints.
- Changing workflow/runtime files.
- Replacing the existing demo story deep-link contract.

## Acceptance Criteria

- RED frontend tests prove the session inbox/dashboard contract is missing before implementation.
- Focused frontend tests prove the inbox is operator-scoped, renders seeded session details, derives status/last-activity summaries, and preserves row-to-story selection.
- Frontend rem gate passes for touched Vue/CSS files.
- Full relevant frontend unit tests pass.
- Browser UAT against `scripts/dev.sh` verifies at least two seeded sessions are visible, switching works, and there is no horizontal overflow.

## Evidence

Evidence lives under `artifacts/slices/121-customer-assistant-session-inbox-dashboard/121.1/`.

- RED: `red.txt`
- Focused frontend unit: `frontend-focused.txt`
- Frontend rem gate: `frontend-rem.txt`
- Full frontend unit: `frontend-unit-full.txt`
- Browser UAT output: `uat.txt`
- Browser UAT notes: `uat.md`
- Screenshot(s): `screenshots/`
- Seed evidence: `seed.txt`
