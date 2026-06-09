# Spec 041: Runtime Policy Config And Observability

## Goal

Move runtime-lab routing parameters from environment-only/demo wiring into a
backend configurable `RuntimePolicyProfile`, and persist every route decision
with the exact policy snapshot used for that decision.

041 does not build frontend UI. It provides backend models and APIs that a host
production system can call to operate classifier, fallback Agent, threshold,
knowledge, and handoff routing parameters.

## Dependency

041 starts only after 033 and 036-040 are complete enough to expose the route
layers that need configuration:

- handoff foundation;
- FAQ exact and semantic gates;
- SOP/task arbitration;
- RAG answer gate;
- controlled fallback Agent;
- final E2E route evidence matrix.

After the 2026-06-09 architecture revision, 041 configures unified candidate
recall, central arbitration, and PolicyGate parameters rather than independent
per-layer early-exit gates.

## Baseline Before 041 Implementation

Available before 041:

- LLM intent classifier can be configured through env:
  - `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE`;
  - `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_BASE_URL`;
  - `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_API_KEY`;
  - `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODEL`;
  - `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_FALLBACK_MODEL`.
- FAQ/RAG knowledge-base bindings can be configured through env.
- Fallback Agent is a `FallbackAgentPort`, but runtime-lab API wiring currently
  instantiates `FakeFallbackAgent()`.
- Thresholds exist as code defaults across policy/classifier/FAQ/RAG/Agent
  candidate/gate code.
- Route evidence is returned per response.

Missing before 041:

- no DB-backed policy profile;
- no host-facing API for route parameters;
- no versioned profile snapshot per decision;
- no backend-configurable fallback Agent binding;
- no backend-configurable classifier prompt/model/runtime params;
- no decision-log query API for evaluation and operations;
- no profile binding by tenant/bot/channel/session.

## Scope

In scope:

- `RuntimePolicyProfile` persistence model;
- `RuntimeDecisionLog` persistence model;
- policy resolver for tenant/bot/channel/session;
- backend APIs to create, update, query, and preview policy profiles;
- backend APIs to query decision logs;
- runtime-lab service consumes active profile instead of only env defaults;
- every decision log stores the full effective policy snapshot;
- env remains bootstrap fallback only.

Out of scope:

- frontend management UI;
- release activation gate and rollback workflow, reserved for 042;
- online learning or automatic threshold tuning;
- changing Chatflow internals;
- changing Knowledge retrieval internals.

## Runtime Policy Profile

Profile states in 041:

```text
draft
active
archived
```

042 will add validation, release, canary, and rollback gates.

Required profile fields:

```text
id
name
description
status
version
mode: strict | balanced | recall_first | custom
bindings:
  tenant_id
  bot_id
  channel
  sop_group
thresholds:
  strong_accept_threshold
  classifier_min_confidence
  candidate_top_k
  candidate_source_weights
  faq_keyword_min_score
  faq_keyword_min_margin
  faq_semantic_min_score
  faq_semantic_min_margin
  rag_min_score
  rag_lexical_accept_threshold
  llm_arbitration_required_for_non_hard_stop
classifier:
  enabled
  mode: fake | llm
  provider_type
  base_url
  api_key_ref
  model
  fallback_model
  prompt_template
  temperature
  max_tokens
  timeout_seconds
  max_attempts
  retry_sleep_seconds
  response_format
faq:
  knowledge_base_ids
  exact_enabled
  semantic_enabled
  top_k
  rerank
rag:
  enabled
  knowledge_base_ids
  retrieval_mode
  top_k
  rerank
fallback_agent:
  enabled
  type: fake | llm_agent | existing_agent | external_webhook
  agent_id
  model_config_id
  provider_type
  base_url
  api_key_ref
  model
  prompt_template
  knowledge_base_ids
  max_clarification_attempts
  allowed_response_types
  handoff_recommendation_policy
handoff:
  enabled
  trigger_groups
  queue
  escalation_reason_map
audit:
  created_by
  updated_by
  change_reason
  created_at
  updated_at
```

Secrets must not be stored directly in logs. Use `api_key_ref` or masked
metadata in snapshots.

## Runtime Decision Log

Every message routed through runtime-lab must persist:

```text
id
session_id
message_id
user_message
active_task_snapshot
suspended_task_snapshot
policy_profile_id
policy_profile_version
policy_snapshot
candidate_scores
faq_score
faq_margin
semantic_score
semantic_margin
rag_score
rag_lexical_overlap
classifier_confidence
agent_confidence
final_action
source_layer
reason_code
mutates_sop_state
handoff_triggered
route_evidence
created_at
```

The log must preserve the effective policy snapshot used at decision time, even
if the profile is later edited or archived.

## Backend API

Host-facing profile APIs:

```text
GET  /api/v1/runtime-policy/profiles
POST /api/v1/runtime-policy/profiles
GET  /api/v1/runtime-policy/profiles/{profile_id}
PUT  /api/v1/runtime-policy/profiles/{profile_id}
POST /api/v1/runtime-policy/profiles/{profile_id}/preview
GET  /api/v1/runtime-policy/effective-profile
```

Host-facing decision-log APIs:

```text
GET /api/v1/runtime-policy/decision-logs
GET /api/v1/runtime-policy/decision-logs/{log_id}
GET /api/v1/runtime-policy/sessions/{session_id}/decision-logs
```

041 must not expose activation without 042's release gate.

## SDD Boundary

Runtime-lab may call policy-profile services through a resolver/facade. Existing
Chatflow, Knowledge, Provider, and Agent modules must remain independent.

No frontend work is required. Swagger/API-level acceptance is sufficient.

## Acceptance Criteria

- policy profile CRUD works through backend API;
- profile schema validates thresholds, classifier config, FAQ/RAG config,
  fallback Agent config, and handoff config;
- runtime-lab can resolve an effective profile for a request;
- env settings are used only when no active profile exists;
- classifier config can be sourced from profile;
- fallback Agent config can be sourced from profile instead of hardcoded fake;
- decision log persists final action, evidence, and effective policy snapshot;
- decision-log API can filter by session, profile, action, source layer, and
  time range;
- no frontend files are modified;
- existing 040 route matrix behavior remains compatible under default profile.

Architecture revision acceptance:

- profile can configure candidate recall topK, source weights, and classifier
  threshold in one policy object;
- profile snapshot records whether non-hard-stop decisions required central
  arbitration;
- decision logs can distinguish hard-stop exits from arbitrated decisions.

## Completion Capability

After 041, a host production system can configure runtime routing parameters
through backend APIs and audit every dialogue decision with the exact policy
configuration that produced it.

## Specification Sign-off

Status: complete.

041 is a backend-only configuration and observability spec. It must not
implement release activation, rollback, or frontend configuration UI.

## Implementation Status

- 041.1 complete: `RuntimePolicyProfile` persistence, backend CRUD API,
  nested policy validation, and Swagger/browser UAT evidence are recorded under
  `artifacts/slices/041-runtime-policy-config-observability/041.1/`.
- 041.2 complete: `RuntimePolicyResolver`, env bootstrap fallback,
  effective-profile API, and runtime-lab config consumption of profile
  classifier/FAQ/RAG sections are recorded under
  `artifacts/slices/041-runtime-policy-config-observability/041.2/`.
- 041.3 complete: profile-driven classifier factory, fallback Agent factory,
  fallback output policy, and runtime-lab service wiring are recorded under
  `artifacts/slices/041-runtime-policy-config-observability/041.3/`.
- 041.4 complete: decision-log persistence, policy snapshot capture,
  query/filter APIs, 040 matrix compatibility, and browser UAT evidence are
  recorded under
  `artifacts/slices/041-runtime-policy-config-observability/041.4/`.
- 041.R1 complete: latest routing architecture profile wiring now proves that
  `classifierMinConfidence`, `candidateTopK`, `candidateSourceWeights`,
  FAQ enable switches, `ragMinScore`, and `ragLexicalAcceptThreshold` are
  consumed by runtime-lab rather than only persisted. Evidence:
  - RED:
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/red-profile-runtime-wiring.txt`,
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/red-rag-lexical-threshold.txt`,
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/red-candidate-top-k.txt`
  - GREEN/runtime policy:
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/green-runtime-policy-runtime-api-full.txt`,
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/runtime-policy-041-042-gate-after-invariant.txt`
  - Runtime-lab regression:
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/runtime-lab-unit-contract-integration-after-invariant.txt`,
    `artifacts/slices/041-runtime-policy-config-observability/041.R1/runtime-lab-e2e-policy-gate-after-invariant.txt`
