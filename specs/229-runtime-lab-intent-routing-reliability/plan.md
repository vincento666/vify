# Plan — Spec 229

## Target Pipeline

```text
hard stops
  -> source candidate observations
  -> CandidateFusionPolicy
  -> canonical Top-K
  -> post-fusion margin gate
  -> shared classifier + Spec 228 uncertainty gate
  -> Policy Gate
```

`RouteContextSnapshotBuilder` runs before recall/classification and receives
read-only adapters for the RuntimeLab ledger, child Chatflow state, transcript,
effective policy, and Intent Catalog.

## 229.1 Candidate Fusion

Introduce source observations without breaking public `RouteCandidate`.
Fusion is a pure deterministic function. Preserve provenance under an additive
`sourceEvidence` field.

RED includes:

- explicit and semantic `sop:refund_ticket` duplicates;
- same FAQ target from exact and semantic lanes;
- stable ordering on equal score;
- conflicting payload fail-closed;
- Top-K capacity counted after fusion.

Avoid probabilistic score inflation in this contract. Maximum weighted score is
explainable and preserves existing threshold intuition.

## 229.2 Margin Policy

Add `candidateMinMargin` to policy schema, resolver, snapshots, validation,
decision logs, replay, and API. Default is `0.12`, matching the original
semantic-routing design.

Margin runs after fusion and before classifier acceptance. Record top IDs,
scores, margin, threshold, and outcome. A low margin cannot be recovered into a
task mutation.

## 229.3 Route Context

Extract the existing handoff context assembly into reusable read-only
components without changing handoff behavior. Current step and waiting state
use the child runtime/checkpoint path already documented by
`docs/chatflow-sop-state-boundary.md`.

Build a separate safe classifier projection:

- identities and statuses;
- derived current step;
- slot names/presence;
- recent route transitions;
- redacted bounded transcript;
- no raw business values.

Tests must snapshot database writes before/after context construction and prove
no RuntimeLab execution mirrors are added.

## 229.4 Intent Catalog

Create code-first definitions adjacent to routing domain code. Validate:

- unique intent IDs and target SOPs;
- existing target manifest exists;
- symmetric/conflict-safe confusable references;
- examples and negative examples are non-empty;
- risk, `intent_kind`, prerequisite, and slot names use allowed enums/schema;
- deterministic version independent of dictionary insertion order.

Route evidence and eval reports record schema/catalog versions.

## 229.5 Intent Retriever

Define `IntentRetrieverPort` and local deterministic implementation. Replace
direct use of scattered SOP semantic constants only after parity/quality RED is
captured. FAQ/RAG answer retrievers remain untouched.

An architectural test prevents:

- answer Knowledge clients from being injected as intent retrievers;
- answer snippets entering classifier payload;
- RuntimeLab Catalog importing Chatflow implementation state.

## 229.6 Verification

- Unit: fusion, margin, context projection, catalog validation/version,
  retriever.
- Integration: MySQL multi-turn context, no mirrors, active/suspended routes.
- Contract: policy fields and additive route evidence.
- E2E: FAQ/SOP/RAG/Agent confusion matrices and airline scale suite.
- Browser: fused source evidence, targeted low-margin clarification,
  multi-turn ellipsis, catalog version.
- Quality report: Recall@5, Macro-F1, mutation violations, latency/payload size.

## Rollback

Feature composition must preserve a local adapter seam so fusion/context/catalog
can be disabled only for diagnosis in test configuration. Production release
cannot activate a profile that bypasses required fusion or margin invariants.

## Risks

- fusion can hide conflicting payloads;
- context can leak PII or create a second truth;
- catalog duplicates SOP execution definitions;
- retrieval replacement can improve recall but lower precision.

Negative tests and Spec 228 real-route evaluation are required mitigations.
