# 025.7 RED Note

This slice hardened behavior that already existed in the current worktree:
`insertWorkflowNodeOnEdge` already removed the original edge, inserted the new
node, and reconnected both sides.

New regression tests were added for the required acceptance behavior:

- branch condition preservation when inserting on a conditional edge;
- midpoint `+` palette insertion;
- inserted node selection/config panel open;
- original edge removal and no duplicate edge.

Because the implementation was already present, the newly added regression tests
did not naturally fail. No implementation was intentionally broken to fabricate
a RED result.
