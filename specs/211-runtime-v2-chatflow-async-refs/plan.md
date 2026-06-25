# Plan 211: Runtime V2 Chatflow Async Refs Closure

## Slices

1. Add Chatflow `/runs:stream` with contract/e2e coverage over success,
   failure, waiting input, reconnect, `_testLimit`, and heartbeat behavior.
2. Add a shared `RuntimeInvocationGateway` for runtime-v2 start/resume
   semantics and route Workflow/Chatflow public gateways through it.
3. Move SOP adapter v2 execution onto the shared gateway and add an async refs
   mode that can return before runtime completion.
4. Move customer-assistant `chatflow_sop` worker behavior toward async runtime
   refs and expose consistent blocking/recommendation metadata.
5. Add standalone worker owner filtering for Workflow, Chatflow, or both.
6. Update docs and browser UAT evidence for stream/ref endpoint matrix and
   visible runtime states.

## Verification

- Backend unit, integration, contract, and e2e tests for each slice.
- Frontend unit and `remScaleClosure` only when frontend visual files change.
- Browser UAT for runtime-lab SOP, customer-assistant task panel, and canvas
  runtime state changes.
- Per-slice evidence under `artifacts/slices/211-runtime-v2-chatflow-async-refs/`.
