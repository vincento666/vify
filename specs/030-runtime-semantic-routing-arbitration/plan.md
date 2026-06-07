# Plan 030: Runtime Semantic Routing Arbitration

## Architecture

Extend `app/modules/runtime_lab` with a candidate-oriented routing pipeline.
The module remains isolated and continues to execute only mock SOPs.

Suggested additions:

```text
app/modules/runtime_lab/
  domain/
    candidates.py
    classifier.py
    policy.py
    recall.py
```

The exact file layout can vary if the current module shape suggests a smaller
edit, but the concepts must stay separate:

- recall produces candidates;
- classifier arbitrates finite candidates;
- policy gate controls early exit and final decision;
- mock SOP adapter executes selected SOP actions.

## Routing Pipeline

```text
RuntimeService.handle_command
  -> RuntimeRouter.build_context
  -> ExplicitSignalDetector.detect
  -> CandidateRecall.recall
  -> PolicyGate.evaluate_pre_classifier
  -> ConstrainedIntentClassifier.classify if required
  -> PolicyGate.evaluate_post_classifier
  -> RuntimeService.apply_decision
```

The service remains the transaction owner.

## Candidate Sources

### ExplicitSignalDetector

Responsibilities:

- exact resume phrases;
- strong mock SOP trigger keywords;
- ordinal references to the current resume offer;
- explicit no-op or refusal phrase candidates.

Output is normalized into candidate records with score evidence.

### CandidateRecall

Responsibilities:

- active task candidate;
- suspended task candidates;
- mock SOP candidates;
- clarify candidate.

030 uses deterministic mock semantic scoring. No external embedding, ES, BM25,
or LLM service is allowed.

### ConstrainedIntentClassifier

Interface:

```text
classify(input: ClassifierInput) -> ClassifierResult
```

The 030 implementation is fake and deterministic, but it must validate:

- allowed action enum;
- candidate membership;
- JSON-like serializable output;
- confidence and clarification fields.

The interface is designed so a later small LLM or traditional NLP model can be
plugged in without changing runtime service behavior.

## Policy Gate

Policy gate is the router controller.

Pre-classifier decisions:

- direct start when no active task and one strong unambiguous SOP candidate;
- direct resume when a current resume offer is explicitly accepted;
- direct clarify when no viable candidate exists;
- require classifier when active task has competing candidates;
- require classifier when candidate margin is too small.

Post-classifier decisions:

- enforce selected candidate membership;
- enforce active non-interruptible switch rejection;
- convert selected action into the existing runtime route action;
- ask clarification when classifier confidence is low;
- keep active task state unchanged for clarification.

## Test Strategy

Unit tests:

- keyword score evidence;
- mock semantic candidate recall;
- finite candidate merging and top-k selection;
- fake classifier membership enforcement;
- policy gate early exit rules;
- policy gate post-classifier rules.

Integration tests:

- no-active strong start without classifier;
- no-active conflict calls classifier once;
- active conflict calls classifier before SOP mutation;
- active non-interruptible switch rejection;
- suspended task candidate resume;
- idempotent replay preserves candidate evidence.

Contract and E2E tests:

- runtime-lab API returns route candidate evidence;
- existing 029 user path remains valid;
- semantic/alias phrasing can start or switch mock SOPs through classifier.

No frontend or browser UAT is required because 030 touches backend API only.

## Evidence

Use:

```text
artifacts/slices/030-runtime-semantic-routing-arbitration/
  030.0/
  030.1/
  030.2/
  ...
```

Each implementation slice saves:

- `red.txt`
- `unit.txt`
- `integration.txt` when relevant
- `contract.txt` when relevant
- `e2e.txt` when relevant
- `ruff.txt`
- `mypy.txt`

## Non-Goals

Do not:

- call existing Chatflow;
- call real LLM providers;
- add vector database dependencies;
- implement FAQ/RAG response policy;
- implement Agent fallback;
- implement human handoff;
- rename the runtime-lab API.

## Git Notes

Commit after spec creation and after each completed implementation slice.
Stage only files that belong to 030.
