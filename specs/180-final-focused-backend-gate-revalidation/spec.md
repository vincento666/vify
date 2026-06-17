# Spec 180: Final Focused Backend Gate Revalidation

## Status

Complete.

## Goal

Refresh focused backend evidence after the MySQL8 demo UAT rerun and recent
configuration hardening. This slice does not add product behavior; it proves the
customer assistant, runtime v2, workflow/chatflow, and MySQL8 gates still pass
on the current branch.

## Functional Requirements

- Run focused customer-assistant integration, contract, and e2e gates.
- Run focused Runtime Lab SOP/runtime-v2 trace gates.
- Run focused workflow/chatflow runtime v2 gates.
- Run focused MySQL8 persistence/write compatibility gates.
- Save outputs under
  `artifacts/slices/180-final-focused-backend-gate-revalidation/180.1/`.

## Non-Goals

- Do not run live provider gates in this slice.
- Do not run full frontend unit/build/rem; those remain final gate work.
- Do not change production code unless a focused gate exposes a real regression.

## Acceptance Criteria

- [x] All selected focused gates pass or expose a tracked follow-up slice with
  RED evidence and a fix.
- [x] MySQL8-only boundary remains green.
- [x] The worktree remains clean except unrelated pre-existing files.

## Evidence

Evidence is saved under
`artifacts/slices/180-final-focused-backend-gate-revalidation/180.1/`.

- Customer assistant:
  `customer-assistant-integration.txt`, `customer-assistant-contract.txt`, and
  `customer-assistant-react-e2e.txt` passed.
- Runtime Lab:
  `runtime-lab-sop-e2e.txt` and `runtime-lab-trace-integration.txt` passed.
- Workflow/chatflow:
  `workflow-runtime-v2-core.txt`,
  `workflow-runtime-v2-lifecycle-versioning.txt`, and
  `workflow-llm-rag-nodes.txt` passed against disposable MySQL8 databases.
- MySQL8:
  `mysql8-boundary.txt` and `mysql8-focused.txt` passed.
- The artifact scan found no `sqlite://`, disposable SQLite database strings,
  historical `hify-uat.db` marker, or OpenRouter API key material.

## Notes

`workflow-llm-rag-nodes-preinit-fail.txt` is retained as RED evidence for the
expected missing-table failure when the disposable MySQL8 database is not
initialised before running those integration tests. The final gate initialises
the same MySQL8 boundary first and passes.
