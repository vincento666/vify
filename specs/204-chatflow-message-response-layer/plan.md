# Plan

## 204.1 Chatflow Message Response Summary

1. RED contract: extend the Chatflow session gateway contract to require Phase 8
   summary fields on a completed message turn.
2. GREEN implementation: project runtime result summary fields into
   `_chatflow_message_response`.
3. Gates: focused Chatflow contract, workflow/runtime backend regression,
   frontend rem closure, full frontend unit, and browser UAT.

## Risk Controls

- Keep legacy `output`, `checkpoint`, and runtime refs in place for existing
  consumers during this additive slice.
- Keep simplified events payload-free.
- Do not modify execution, idempotency, or worker behavior.
