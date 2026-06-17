# Plan: Customer Assistant Session Inbox Dashboard MVP

## Scope

Build a frontend-only operator session inbox for the seeded MVP workbench. Reuse the existing customer-assistant demo story APIs and runtime loader so the inbox is a visibility and navigation layer, not a second runtime path.

## Data Flow

1. Load seeded stories through `listCustomerAssistantDemoStories()`.
2. Load aggregate and per-story metrics through `getCustomerAssistantDemoStoryMetrics()`.
3. Merge story rows and metric rows by `storyId`.
4. Present rows as session inbox items with status hints:
   - blocked when task metrics contain `WAITING`, `FAILED`, or recent failure reasons;
   - pending when pending actions are present;
   - completed when all tasks are completed and no pending action remains;
   - active otherwise.
5. On row selection, call the existing `loadDemoStory(storyId)` flow, which loads ledgers, updates selected story state, and syncs the route query.

## Frontend Work

- Add typed session inbox helpers in `customerAssistantRuntime.ts`.
- Add unit coverage for inbox row merging and status hint derivation.
- Add `CustomerAssistantPanel.vue` markup and styles for an operator-area inbox above the conversation/workbench grid.
- Extend the panel UI contract test to keep inbox controls out of the customer lane.
- Add a focused browser UAT script for seeded session inbox visibility and switching.

## Verification

- Capture RED output before implementation.
- Run focused customer-assistant frontend tests.
- Run the rem unit gate because the Vue/CSS surface changes.
- Run full frontend unit tests.
- Run `scripts/dev.sh` and browser UAT with seeded data, saving output and screenshots.

## Result

Implemented in slice 121.1 as a frontend-only session inbox/dashboard backed by existing seeded demo story and metrics APIs.
