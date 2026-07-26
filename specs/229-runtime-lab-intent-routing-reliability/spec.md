# Spec 229: RuntimeLab Intent Routing Reliability

Status: accepted on 2026-07-26; depends on Spec 228 Goal Gate.

## Problem

RuntimeLab combines explicit, semantic, FAQ, RAG, and Agent candidates by
concatenating and truncating them. The same target can occupy multiple Top-K
positions, making confidence margin unreliable. The real classifier receives
only a thin active/suspended summary. Intent-selection knowledge is duplicated
across SOP manifests and recall constants, and is not versioned or separated
from answer knowledge.

## Intended Outcome

Produce one canonical candidate per target, reason over a bounded read-only
multi-turn context, and retrieve versioned intent definitions from a corpus
that is isolated from FAQ/RAG answer content.

## Scope

### In Scope

- deterministic multi-source candidate fusion before Top-K;
- Top-1/Top-2 margin enforcement after fusion;
- policy field `candidateMinMargin`, default `0.12`;
- read-only `RouteContextSnapshot` derived from RuntimeLab ledger plus child
  Chatflow state;
- bounded/redacted `ClassifierContextProjection`;
- code-first versioned `IntentDefinition` and `IntentCatalog`;
- an independent `IntentRetrieverPort` and deterministic local implementation;
- catalog/version/evidence projection in route logs and evaluation;
- RuntimeLab inspector support for fused sources, context summary, and catalog
  version.

### Out Of Scope

- copying child Chatflow execution state into RuntimeLab tables/events;
- Catalog database authoring or administration UI;
- mandatory embedding/provider calls;
- generic model training or BERT;
- answer generation from the intent corpus;
- authorization/confirmation, owned by Spec 230;
- composite routing, owned by Spec 231.

## Candidate Fusion Contract

Canonical identity:

```text
candidate_key = candidate_type + ":" + target_id
```

Fusion:

- apply configured source weight to each source observation;
- each weighted score is `clamp(raw_score * source_weight, 0, 1)`;
- canonical score is the maximum weighted source score;
- preserve every source observation and raw/weighted score;
- union matched terms in stable order;
- use the highest risk class under `LOW < MEDIUM < HIGH`;
- `requires_classifier` is the safe OR of source requirements;
- stable tie-breaker is canonical key;
- Top-K and margin are computed only after fusion.

If two candidates have incompatible payloads for one canonical key, fusion
must fail closed to CLARIFY with evidence; it must not silently select one
payload.

## Margin Contract

After fusion:

```text
top1.score - top2.score < candidateMinMargin
=> CLARIFY
=> no task mutation
```

Hard-stop handoff remains the only pre-arbitration final exit. A sole viable
candidate has no margin ambiguity but still passes Spec 228 confidence policy.

## RouteContextSnapshot Contract

Snapshot fields:

```text
session/turn ids
current user message
active task summary
suspended task summaries
child-derived current step / pending node
known slot names / missing slot names
bounded recent route transitions
bounded transcript summary
enabled intent ids
policy profile/version
intent catalog/version
```

Ownership:

- RuntimeLab owns route ledger, task identity/status, and child refs;
- child Chatflow owns current step, waiting prompt, variables, checkpoint,
  node events, and run state;
- snapshot is derived for one decision and is not persisted as a second
  execution truth.

LLM projection limits:

- at most six recent turns and 2,000 normalized transcript characters;
- slot names/presence only by default, never phone/order/document values;
- secret-key filtering and explicit allowlist;
- serialized classifier payload at most 12 KiB;
- truncation is deterministic and reported as evidence.

## Intent Catalog Contract

Each code-first definition includes:

```text
intent_id
definition_version
display_name
description
positive_examples
negative_examples
confusable_intent_ids
eligibility / prerequisites
required_slot_names
risk_class
intent_kind: READ_ONLY_CONSULTATION | TRANSACTIONAL
route_target_sop_id
```

The Catalog describes selection semantics. It references, but does not copy,
Chatflow steps or execution prompts. Catalog version is a deterministic content
hash plus schema version.

Intent retrieval has a separate port, configuration key, collection/index
identity, metrics, and evidence from FAQ/RAG answer retrieval. Answer documents
and snippets are forbidden classifier inputs. The required implementation is
local deterministic lexical/BM25-lite/character-vector retrieval over
definitions; a provider-backed embedding adapter needs a future accepted
contract.

## Quality Targets

- duplicate canonical IDs presented to the classifier: `0`;
- frozen required-set candidate Recall@5: `>= 0.98`;
- frozen required-set route Macro-F1: `>= 0.95` and not below Spec 228 baseline;
- state-transition violations on clarification/answer-only paths: `0`;
- RouteContextSnapshot child-state parity cases: `100%`;
- raw sensitive slot values in classifier payload: `0`;
- default external provider calls: `0`.

## Public Compatibility

- existing candidate fields remain; fused provenance is additive;
- existing action values and API/SSE envelopes remain;
- `candidateMinMargin`, context evidence, and catalog version are additive;
- idempotent replay preserves fused ordering and catalog version.

## Slices

1. `229.1` canonical candidate fusion.
2. `229.2` post-fusion margin policy.
3. `229.3` RouteContextSnapshot and safe classifier projection.
4. `229.4` versioned Intent Catalog.
5. `229.5` isolated Intent Retriever.
6. `229.6` quality, browser, and Goal Gate.

## Success Predicate

Spec 229 is satisfied when all quality targets and compatibility gates pass,
child Chatflow remains the sole execution-state truth, and independent Checker
and Reviewer accept the full diff and evidence.

## Goal Controls

- max attempts: 3 per slice;
- inherits the 21-day outer TTL;
- budget: 0 live/paid provider calls;
- on exhaustion: `WAITING_HUMAN`;
- review context: standard.

## Human Gates And Authority

Accepted as part of the user-authorized Spec 228-231 sequence on 2026-07-26.
Slice commits and branch push are authorized.

Provider-backed retrieval, new dependencies, database-authored Catalog/UI, PR,
merge, deployment, and production writes remain unauthorized.
