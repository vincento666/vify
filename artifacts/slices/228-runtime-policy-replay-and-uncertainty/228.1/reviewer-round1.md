# 228.1 Reviewer Round 1

- Verdict: REQUEST CHANGES
- HIGH: required cases could omit frozen route-contract evidence and still pass.
- HIGH: contradictory provider counters could bypass zero-provider gate.
- HIGH: runner output was copied verbatim, permitting secrets/raw provider payloads in reports.
- MEDIUM: focused mypy reported five errors across touched source files.

Directed repair round: 1 / 3.

Fixes:

- required cases now require presence of initial context, enabled intents, policy snapshot,
  classifier fixture, recalled candidates, target, and clarification evidence;
- any non-zero provider counter fails budget; contradictory totals add an inconsistency reason;
- runner output uses a strict route-evidence whitelist; unexpected fields are dropped and fail
  evaluation without persisting values;
- focused mypy is green.
