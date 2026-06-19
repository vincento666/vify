# Plan

## 206.1 Customer Assistant Message Response Summary

1. RED contract: require Phase 8 summary fields on the message gateway response.
2. GREEN implementation: derive summary fields from existing turn payload events
   and task summaries.
3. Gates: focused customer-assistant contract, customer-assistant contract
   regression, frontend rem/full unit, workflow runtime backend gate, and browser
   UAT.

## Risk Controls

- Do not alter async worker runtime code already dirty in the worktree.
- Keep full `events` compatibility for current frontend runtime state.
- Do not expose event `payload` in `eventSummary`.
