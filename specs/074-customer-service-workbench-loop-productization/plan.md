# 074 Plan

## 074.1 Seeded Story Picker And Load Path

Implementation shape:

- Add a read endpoint under `/api/v1/customer-assistant/demo-stories`.
- The endpoint scans existing 073 seed session context and returns stable story
  metadata plus session IDs, without exposing secrets.
- Add API/client/runtime helpers to list stories and load a selected session's
  ledgers.
- Add a compact story selector to `CustomerAssistantPanel.vue`.
- Keep all new frontend visual sizing in `rem`.

TDD seams:

- RED backend integration test: after running `seed_mvp_demo`, demo stories are
  not discoverable through the customer-assistant API.
- RED frontend unit test: runtime cannot load a seeded story into the workbench.
- GREEN backend endpoint and frontend API/runtime helpers.
- Browser UAT: seed temp DB, open `/customer-assistant`, select a story, verify
  task ledger, proposed actions, and event timeline are visible.

## 074.2 Human Task Control Loop

Implementation shape:

- Add task-row actions for retry/cancel/resume.
- Use proposed action confirmation rather than direct writes.
- Refresh tasks/events after every control.

## 074.3 Knowledge-Backed Operator Advisory

Implementation shape:

- Read session `knowledgeBaseIds` and deterministic FAQ material from 073.
- Enrich operator advisory context with knowledge hits and current task state.
- Preserve explicit warnings when knowledge bindings are absent.

## Gates

Each slice must save RED, unit, integration/contract, frontend/rem where needed,
E2E, browser UAT, and docs evidence before commit.
