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

## 069.6 Main Runtime ReAct Progression Audit Gap

- [x] RED: Two-Stage primary path did not record sanitized main-runtime
      plan/action/observation progression.
- [x] Emit debug-only `two_stage_plan_recorded`,
      `two_stage_action_recorded`, and `two_stage_observation_recorded`
      events derived from the controlled core observation.
- [x] Add `reactStep=final` and `legacyStage=generate_recommendation` to
      Two-Stage final selection/fallback/shadow decision events.
- [x] Preserve existing `task_recognized`, worker/recommendation events, and
      response schema.
- [x] Prove no raw chain-of-thought field is persisted in the progression
      payloads.

## 069 Evidence

- RED: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/red.txt`
- RED threshold: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/red-equivalence-threshold.txt`
- Unit: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/unit.txt`
- Focused/integration: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/focused.txt`
- Backend gate: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/backend-gates.txt`
- E2E: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/e2e.txt`
- Browser UAT: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/uat.md`
- Promotion threshold: `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/equivalence-threshold.md`
- 069.6 RED:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/red.txt`
- 069.6 Focused:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/focused.txt`
- 069.6 Integration:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/integration.txt`
- 069.6 Customer-assistant focused gate:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/customer-assistant-focused.txt`
- 069.6 Customer-assistant integration gate:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/customer-assistant-integration-all.txt`
- 069.6 Customer-assistant unit gate:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/customer-assistant-unit-all.txt`
- 069.6 Ruff:
  `artifacts/slices/069-customer-assistant-two-stage-react-runtime-mvp/069.6/ruff.txt`
