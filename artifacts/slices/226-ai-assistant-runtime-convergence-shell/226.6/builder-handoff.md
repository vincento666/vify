# Builder Handoff — 226.6

TDD method: `tdd`

## Scope

- Replaced the link-era child reference DTO with a bounded public Agent
  Execution module: typed capabilities, provider operations, immutable
  lifecycle refs, stable correlation helpers, and a terminal-monotonic state
  machine.
- Customer Assistant now supplies a real persisted provider Adapter. Attach
  and observe return actual run status, timestamps, scope, audit and durable
  status/event/result refs. Unsupported spawn/cancel are explicit
  capabilities and typed errors, not placeholder success.
- AI Assistant consumes only the public provider Interface. HTTP and
  standalone workers receive the Customer implementation at composition
  roots; neither AI domain code nor the public module imports Customer.
- Durable worker execution restores the verified run scope and a validated
  principal org before child attach. Customer owner checks now enforce tenant
  and org for both ordinary service calls and child-provider calls.
- Tool, Skill, phase, plan-step, approval and subagent events receive stable
  activity correlation. A real attached child emits a parent-ledger
  `subagent.execution_*` event with parent activity and execution refs.
- Added a pure frontend RunActivity projection. It deduplicates durable event
  replay, sorts reordered input, preserves terminal status and identity,
  exposes raw event IDs/range, and excludes legacy/link-only events without a
  stable correlation.

## RED

- `red-activity-projection.txt`
- `red-agent-execution.txt`
- `red-durable-child-provider.txt`

## GREEN Evidence

See `green.txt`.

## Security And HA Review

- Provider attach verifies session/run identity before returning refs.
- Non-local Customer scope is tenant+org fail-closed; local durable scope is
  restored only after the claimed job resolves a matching durable AI run.
- Durable principal org comes from the persisted, verified execution-scope
  snapshot and is ignored if tenant/actor do not match the run columns.
- Job payload remains reference-only and no secret, raw lease fence or model
  credential is copied into child lifecycle events.
- Parent child facts remain in the existing durable event ledger; there is no
  second activity or child-execution table.

## Explicit Gate Notes

- Browser UAT: N/A. This slice adds projection/state contracts but does not
  render the new shell; Browser UAT is mandatory in 226.7.
- rem gate: N/A. No visual CSS or dimensions changed.
- Live provider: N/A. External model/provider calls remained zero.
- Migration/deploy: N/A. No schema change and no deployment authorization.
- Customer child execution: attach/observe uses a persisted lifecycle, while
  spawn/cancel remain unsupported. Continuous cross-ledger observation is not
  claimed by this slice; 226.7 may render attached running and terminal
  snapshots, and a future provider capability must be explicit if added.

## Remaining Contract

- 226.7: Hify light activity shell, expansion overrides, real child presence,
  approval/error treatment, rem/a11y, Browser UAT and screenshots.
- 226.8: evidence-gated cleanup of sequence-range presentation, default
  demo/stub tools and remaining compatibility paths.
