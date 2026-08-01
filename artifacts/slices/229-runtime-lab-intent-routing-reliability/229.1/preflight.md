# 229.1 preflight

Date: 2026-07-27

- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`.
- Base delivery: `1c30e6e5` (Spec 228 delivery snapshot).
- Scope: canonical candidate fusion only. No margin, context snapshot, catalog,
  retriever, provider, migration, authorization, or composite route work.
- Provider budget: zero. All fixtures are deterministic/local.
- MySQL capability: repository `mysql8` compose service healthy. Weaviate off.
- Existing public envelopes and Chatflow execution-state ownership are retained.

Renewed corrective preflight — 2026-08-01

- User explicitly authorized continuation beyond the prior local repair cap.
- Branch and worktree remain unchanged; external Loop harness edits remain
  unstaged and excluded from this slice.
- `mysql8` is healthy. Tests use only the repository-supported disposable
  database admin capability; Weaviate remains off because no frozen test needs it.
- Provider budget remains zero; all routing and Chatflow fixtures are local and
  deterministic.
