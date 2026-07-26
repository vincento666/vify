# Plan — Spec 231

## Design Summary

Composite intent is a routing representation, not a second workflow runtime.
The detector consumes Spec 229 fused candidates and produces a bounded plan.
RuntimeLab persists the plan as route-ledger evidence and resolves one selected
component through the normal Spec 230 gate.

```text
user turn
  -> fused canonical candidates
  -> AtomicIntentDetector
  -> CompositeIntentPolicy
       -> single intent: existing route path
       -> composite: clarify or answer-and-offer
            -> route-ledger pending plan
                 -> explicit user resolution
                      -> fresh RouteExecutionGate
                           -> existing one-active/one-suspended dispatch
```

## 231.1 Atomic Components And Detection

Introduce pure domain types for atomic components, relation, and result. Start
with deterministic clause/connector parsing over enabled canonical candidates.
An optional classifier adapter receives only candidate IDs and supported
relations and must pass strict membership validation.

RED:

- the current refund-plus-invoice phrase becomes one `START_SOP`;
- an unknown clause can be returned as a model-created target;
- repeated observations become repeated components.

GREEN:

- both canonical components survive;
- `先...再...` becomes `THEN`;
- ambiguous conjunction becomes `AND` plus clarification;
- disabled/unknown targets remain visible as unmatched evidence but are not
  invented as executable components;
- single-intent input stays on the existing route path.

Keep parsing narrow. Add connector families only from frozen failing cases; do
not build a general natural-language parser.

## 231.2 Clarification And Ledger Plan

Add a composite branch before any task mutation. For multiple transactional
components, build a targeted question and append
`COMPOSITE_INTENT_DETECTED` to the existing route ledger.

The stored payload includes:

- component candidate/intent IDs and evidence refs;
- relation and optional explicit primary;
- session/state/policy/catalog versions;
- turn-based expiry and stable plan hash;
- assistant question or offer;
- no raw slot values or provider payload.

Resolution matches a bounded explicit choice against pending components. It
marks the plan resolved once, re-reads task state/candidates, and invokes the
normal route/execution gates. Idempotent replay returns the original turn
result without resolving twice.

## 231.3 Consultation Plus Transaction

Classify intent definitions with behavior metadata sufficient to distinguish a
read-only deterministic consultation from a transactional SOP. Do not infer
this from `risk_class` alone.

When exactly one safe consultation and one transaction are present:

1. answer through the existing deterministic read-only answer gate;
2. return `nextActionOffer` for the transaction;
3. persist the bounded pending plan;
4. start nothing until explicit acceptance;
5. re-run the execution gate on acceptance.

Any uncertainty, unavailable answer, extra transaction, or unsafe effect falls
back to targeted clarification.

## 231.4 Exit Verification

- Unit: parser, membership validation, relations, expiry, stable plan hash.
- Contract: additive composite/clarification/offer fields and replay.
- Integration: zero mutation counters, ledger lifecycle, fresh gate
  re-evaluation, active/suspended constraints.
- E2E: composite regression, explicit order, consultation-plus-transaction,
  stale and single-intent regression.
- Browser: targeted clarification, component choice, answer-and-offer, expired
  plan, route inspector evidence.
- Review: false-flattening cases, secret scan, scope check, Checker/Reviewer.

## State And Ownership

- RuntimeLab ledger owns pending routing evidence.
- Chatflow owns child execution state and is untouched during detection.
- Spec 230 owns authorization/confirmation.
- Spec 229 owns candidate and catalog truth.
- Spec 228 owns uncertainty and evaluation truth.

No component may copy or override another owner's state.

## Rollback

Additive API fields and ledger events can remain readable if the composite
branch is disabled. Any rollback must return ambiguous multi-intent turns to
`CLARIFY`; it cannot restore silent single-target mutation.

## Risks

- a deterministic parser grows into a brittle general NLP subsystem;
- answer-and-offer accidentally mutates state;
- a pending plan becomes stale authority;
- resolution bypasses permission or confirmation;
- existing interrupt/resume semantics are misclassified as composite.

Mitigations: frozen cases, pure detector, mutation counters, short expiry,
fresh gate evaluation, and focused compatibility regression.
