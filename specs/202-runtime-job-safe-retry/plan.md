# Plan

## Slice 202.1 Workflow Safe Retry From Completed Nodes

1. Add RED contract coverage that seeds a completed first node, runs the
   standalone worker, and asserts the first node is not duplicated.
2. Add runtime helper to replay completed node outputs into `ExecutionContext`.
3. Advance the resume cursor through the active path using existing
   `_next_node_key` routing semantics.
4. Keep fresh-run behavior unchanged.
5. Run focused safe-retry tests, broad runtime/workflow regression, frontend
   rem/unit, and browser UAT.

## Risks

- External side effects are not exactly-once; this slice only prevents duplicate
  execution for nodes already marked `COMPLETED`.
- Complex branch merge reconciliation remains deferred.
