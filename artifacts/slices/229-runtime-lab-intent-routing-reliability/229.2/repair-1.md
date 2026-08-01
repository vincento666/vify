# Repair 1 — fixture isolation

The first frozen matrix run found eight expected-lane failures. Canonical
candidate scores from existing deterministic fixtures can saturate at `1.0`, so
the new default margin correctly produces `CLARIFY` before the older lane
fixtures reach their classifier assertions.

Repair: keep the default gate unchanged and add API/MySQL coverage for it. Set
the pre-existing lane-only fixtures to their explicit zero-margin policy so they
continue to verify FAQ/RAG/SOP classifier routing independently of the new gate.

Re-run result: `37 passed`, with no live provider call.
