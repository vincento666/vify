# 228.5 Goal Gate preflight

Date: 2026-07-26

- method: `tdd`
- unit type: verification-only Contract A Goal Gate; no product write planned
- branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- start HEAD: `c5329942131bf98946a9c39eb081596d0351b173`
- upstream divergence: `0/0`
- worktree: clean
- MySQL: existing compose `mysql8` healthy
- Weaviate: not started; not required
- live/paid provider budget: `0`
- merge/PR/deploy: not authorized

Observable negative sentinel:

- missing shared replay port must fail closed;
- missing required evidence must fail before route execution;
- a known gap cannot create a passing report without required evidence;
- faulting the shared decision must produce the compatible public failure and
  persist no evaluation run.

GREEN matrix:

1. Route-evaluation required/known-gap/zero-provider contract.
2. Shared production replay parity, uncertainty zero-mutation, targeted
   clarification persistence/replay.
3. Complete RuntimeLab MySQL integration and relevant Unit/Contract/E2E.
4. Public envelope and SSE `delta|done|error` regression.
5. Complete frontend, rem, type/build, and 228.4 Browser evidence audit.
6. Ruff/mypy-applicable/diff/secret/migration gates.
7. Independent Checker `ALL GREEN`; independent Reviewer `PASS`.

No Spec 229 product code may be written before this gate closes.
