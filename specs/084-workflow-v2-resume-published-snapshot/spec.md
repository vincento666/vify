# Spec 084: Workflow V2 Resume Published Snapshot

## Goal

Ensure long-running Workflow runtime v2 executions resume against the immutable
published version that started the run, even if the draft workflow graph changes
while the run is interrupted.

## Acceptance Criteria

- A Workflow v2 run started from a published version can interrupt on a
  `QUESTION` node.
- Editing the draft graph while the run is interrupted does not affect the
  resumed run.
- Resuming the run completes with output from the original published snapshot.
- Runtime v2 result metadata still reports the published `versionId` and
  `version`.

## Non-goals

- Do not change draft Chatflow runtime v2 semantics.
- Do not add new node types.
- Do not redesign publish/rollback APIs.

## Evidence

Evidence lives under
`artifacts/slices/084-workflow-v2-resume-published-snapshot/<slice>/`.
