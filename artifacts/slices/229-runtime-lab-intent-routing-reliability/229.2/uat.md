229.2 UAT note

No browser PASS is claimed for this slice.

Reason:
- Spec 229.2 is the post-fusion margin slice.
- The frozen verifier for this slice is unit + MySQL-backed integration / contract / E2E.
- Browser UAT is reserved for 229.3 and 229.6 gates in `specs/229-runtime-lab-intent-routing-reliability/tasks.md`.

Observed user-flow evidence for 229.2:
- low-margin turns return `CLARIFY` before classifier/task mutation;
- decision logs and replay preserve additive `candidateMargin` evidence;
- default `candidateMinMargin` is `0.12` and invalid profile values reject.
