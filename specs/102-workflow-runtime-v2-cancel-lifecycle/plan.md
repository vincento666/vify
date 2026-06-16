# Implementation Plan: Workflow Runtime V2 Cancel Lifecycle

## Slice 102.1 Durable Runtime V2 Cancel

1. Change the existing cancel integration test from unsupported event semantics to durable `CANCELLED` terminal semantics.
2. Save the RED failure before implementation.
3. Implement a narrow runtime v2 cancellation transition in the shared runtime service.
4. Guard background completion against post-delay cancelled/terminal runs.
5. Add browser UAT that starts a runtime v2 run from Chromium, cancels it, waits past the completion delay, and verifies `CANCELLED`.
6. Run focused integration, targeted e2e/browser UAT, and backend smoke gates.
7. Update evidence and commit the focused feature point.

## Evidence Directory

`artifacts/slices/102-workflow-runtime-v2-cancel-lifecycle/102.1/`
