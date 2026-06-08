## Slice Notes

- Scope: commit the existing evaluation run summary metric view-model change as a standalone history recovery slice.
- The worktree already contained both the failing test expectation and the implementation when this slice started, so no artificial RED run was recreated.
- Focused unit, full frontend unit, and frontend build were rerun and passed before commit.
- Browser UAT is not applicable for this view-model-only helper.
