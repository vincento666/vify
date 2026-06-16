# Tasks 069: Customer Assistant Two-Stage ReAct Runtime MVP

## 069.0 Sign-off

- [x] Confirm default behavior remains controlled loop.
- [x] Confirm shadow mode cannot mutate behavior.
- [x] Confirm operator turns remain recommendation-only by default.
- [x] Confirm high-risk writes remain proposed actions.
- [x] Confirm shadow mode cannot dispatch additional workers or side-effecting
      tools.
- [x] Confirm raw chain-of-thought/internal reasoning is not persisted or shown.
- [x] Confirm rollout mode is explicit and reversible.
- [x] Confirm Two-Stage finalization is schema-compatible with
      `generate_recommendation`.
- [x] Confirm waiting Chatflow/worker prompts remain authoritative for customer
      drafts.

## 069.1 Shadow Two-Stage Runtime

- [x] RED: no diff evidence exists between controlled loop and Two-Stage ReAct.
- [x] Add Two-Stage shadow path.
- [x] Persist diff events and eval evidence.
- [x] Prove runtime response is unchanged in shadow mode.
- [x] Prove shadow path does not create worker/tool side effects.

## 069.2 Equivalence Gate

- [x] Compare task commands.
- [x] Compare ledger mutations.
- [x] Compare worker dispatch decisions.
- [x] Compare recommendation/draft/proposed action shape.
- [x] Compare recommendation evidence refs, warnings, waiting reason, and
      checkpoint refs.
- [x] Compare waiting-node customer draft text against worker/node prompt.
- [x] Define pass/fail thresholds over the 054 synthetic/golden suite.
- [x] Block primary selection if equivalence threshold is not met.

## 069.3 Finalizer Contract

- [x] RED: Two-Stage finalizer can produce output not accepted by the existing
      recommendation schema.
- [x] Reuse or wrap the existing recommendation result schema.
- [x] Add finalizer input pack: task ledger, worker results, pending worker
      evidence, blocking-node prompt, proposed actions, safety state, and
      conversation context.
- [x] Add prompt/instruction template that forbids inventing business facts,
      direct writes, and rewriting concrete waiting prompts.
- [x] Add validator that falls back to controlled `generate_recommendation` on
      schema, safety, unsupported field, or prompt-preservation failure.

## 069.4 Opt-in Primary

- [x] RED: opt-in Two-Stage mode cannot select safe output.
- [x] Add feature flag.
- [x] Add reversible rollout modes and default-off config.
- [x] Add fallback policy and fallback events.
- [x] Restrict Stage 2 to allowlisted commands/workers.
- [x] Keep deterministic/controlled default.

## 069.5 UAT

- [x] Verify existing customer task flows remain consistent.
- [x] Verify waiting Chatflow node finalization preserves customer draft text.
- [x] Verify operator advisory remains read-only.
- [x] Verify unsafe action still becomes proposed action.

## 069 Evidence

- RED: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/red.txt`
- RED threshold: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/red-equivalence-threshold.txt`
- Unit: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/unit.txt`
- Focused/integration: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/focused.txt`
- Backend gate: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/backend-gates.txt`
- E2E: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/e2e.txt`
- Browser UAT: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/uat.md`
- Promotion threshold: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/equivalence-threshold.md`
