# Tasks: Customer Assistant AI Workbench IA Convergence

Status: reopened on 2026-06-21 for focus-workbench cleanup and P0 UAT blockers.

## Problem Inventory

- [x] Inventory current issues covering duplicated recommendation, duplicated
  high-sensitive actions, wrong pending count, misplaced SOP tree, thin business
  objects, noisy risk/debug boundaries, seeded action payloads, live multi-task
  500, stale worker profile env, JSON env fragility, and refund recognition gap.
- [x] Evidence:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/00-problem-inventory/problem-inventory.md`

## Slice A: Focus IA And Recommendation Consolidation

- [x] RED: panel contract requires a single production-style focus handling path
  with no legacy peer panels.
- [x] GREEN: task intent/SOP tree is directly below status/next action.
- [x] GREEN: recommended reply card uses `customerReplyDraft` for send/copy/edit
  and shows `operatorRecommendation` only as operator guidance.
- [x] GREEN: high-sensitive confirmation counts only pending actions and shows
  receipts/details through one primary card.
- [x] Gate: focused panel test and remScaleClosure.

## Slice B: Seeded Pending Actions

- [x] RED: seeded demo built-in pending action confirmation fails against old
  payload shape.
- [x] GREEN: seeded task-command actions use the current payload contract and can
  be confirmed/rejected through the API.
- [x] Gate: focused customer-assistant demo seed/task-control tests.

## Slice C: Live Multi-Task Worker Runtime

- [x] RED: reproduce or narrowly guard the known PyMySQL packet sequence failure
  on live multi-task worker persistence.
- [x] GREEN: async worker persistence uses isolated sessions/connections and a
  live multi-task turn does not 500.
- [x] Gate: relevant customer-assistant worker/runtime integration/e2e tests.

## Slice D: Profile Defaults And Refund Recognition

- [ ] RED: default profile catalog must not use stale baggage stub, and
  `退 MU5137 的票` must recognize refund intent.
- [ ] GREEN: local/default profile path is productized and refund natural
  phrasing is recognized.
- [ ] Gate: worker profile and recognition tests.

## Main Verification

- [ ] Backend unit/integration/contract/e2e for touched customer-assistant areas.
- [ ] Frontend focused unit, full unit, and `src/remScaleClosure.test.ts`.
- [ ] Browser UAT covering all right-side tabs, seeded action confirmation, and
  live multi-task recommendation path.
- [ ] Diff review confirms no duplicate legacy focus panels or debug leakage.
- [ ] Commit each accepted sub-feature without staging unrelated dirty files.
