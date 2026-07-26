# Loop Verifiers: RuntimeLab Intent Routing Reliability Program

These commands define the evidence contract. Planned test files are created by
their owning TDD slice; an absent planned file is RED, not N/A. Each command and
result must be copied to the matching `artifacts/slices/<spec>/<slice>/`
directory.

## Contract And Resume Gate

    rtk git status --short --branch
    rtk git rev-parse HEAD
    rtk git worktree list
    rtk git diff --check
    rtk rg -n "Status|Problem|Scope|Success Predicate|Goal Controls|Human Gates" specs/228-runtime-policy-replay-and-uncertainty specs/229-runtime-lab-intent-routing-reliability specs/230-runtime-route-execution-boundary specs/231-runtime-lab-composite-intent
    rtk rg -n "Status|Context|Decision|Options Rejected|Consequences|Guardrails" docs/adr/0010-runtime-route-decision-and-execution-boundary.md
    rtk rg -n "S0|S1|S2|S3|S4|S5|S6|WAITING_HUMAN|provider budget" loop/CURRENT.md loop/STATE.md

## Local MySQL Capability Recovery

Run only when the active gate requires MySQL:

    rtk docker compose -f docker-compose.mysql8-weaviate.yml up -d mysql8
    rtk docker compose -f docker-compose.mysql8-weaviate.yml ps mysql8
    rtk uv run alembic upgrade head
    rtk uv run alembic heads
    rtk uv run alembic check

Do not start Weaviate unless an active frozen test requires it. Failure after
bounded diagnosis is recorded as `ENV-BLOCKED-MYSQL`, never PASS.

## 228.1 Real-route Evaluation Contract

Planned RED/GREEN files:

    rtk uv run pytest tests/unit/runtime_policy/test_route_eval_contract.py tests/unit/runtime_policy/test_replay_service.py tests/unit/runtime_policy/test_governance_validation.py -q --tb=short

Required negative evidence:

- missing replay port fails;
- a deliberately wrong shared-runner result fails;
- missing required case evidence fails;
- `known_gap` never contributes to required PASS;
- provider usage is zero.

## 228.2 Governance Replay Integrity

    rtk uv run pytest tests/unit/runtime_policy/test_replay_service.py tests/contract/test_runtime_policy_replay_api.py tests/contract/test_runtime_policy_governance_validation_api.py -q --tb=short
    rtk uv run pytest tests/integration/runtime_lab/test_runtime_policy_route_replay_parity.py tests/integration/runtime_lab/test_runtime_lab_service.py tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py -q --tb=short

The planned parity test must pass through the MySQL-backed public RuntimeLab
message path and fail when the shared decision implementation is faulted.

## 228.3-228.4 Uncertainty And Clarification

    rtk uv run pytest tests/unit/runtime_lab/test_constrained_classifier.py tests/unit/runtime_lab/test_uncertainty_policy.py tests/unit/runtime_policy/test_profile_schema.py tests/unit/runtime_policy/test_release_service.py -q --tb=short
    rtk uv run pytest tests/contract/test_runtime_lab_semantic_evidence_api.py tests/contract/test_runtime_lab_config_api.py tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py tests/integration/runtime_lab/test_runtime_lab_uncertainty_mutation_gate.py -q --tb=short
    rtk uv run pytest tests/e2e/test_runtime_lab_semantic_api_e2e.py tests/e2e/test_runtime_policy_release_rollback_e2e.py -q --tb=short
    rtk npm --prefix frontend run test:unit -- src/api/runtimeLab.test.ts src/views/chat/runtimeLabSopEventStream.test.ts

Required counters prove zero task/adapter calls for low, invalid, incoherent, or
explicit-clarification outputs. Targeted questions must survive persistence and
idempotent replay.

## 229.1 Candidate Fusion And Margin

    rtk uv run pytest tests/unit/runtime_lab/test_candidates.py tests/unit/runtime_lab/test_candidate_fusion.py tests/unit/runtime_lab/test_candidate_margin_policy.py -q --tb=short
    rtk uv run pytest tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py tests/e2e/test_runtime_lab_confusion_rag_agent_matrix_e2e.py tests/e2e/test_runtime_lab_airline_scale_e2e.py -q --tb=short

Required metrics: duplicate canonical IDs `0`; margin below `0.12` clarifies
with zero mutation; stable ordering and incompatible-payload fail-closed pass.

## 229.2 RouteContextSnapshot

    rtk uv run pytest tests/unit/runtime_lab/test_route_context_snapshot.py tests/unit/runtime_lab/test_business_context_aggregator.py -q --tb=short
    rtk uv run pytest tests/contract/runtime_lab/test_aggregate_from_child_chatflow.py tests/integration/runtime_lab/test_business_context_aggregator_parity.py tests/integration/runtime_lab/test_no_state_mirroring.py tests/integration/runtime_lab/test_service_records_turn_context.py -q --tb=short

Required evidence: child-state parity `100%`, no mirrored execution state,
maximum six turns/2,000 characters/12 KiB, deterministic truncation, and zero
raw sensitive slot values.

## 229.3-229.5 Intent Catalog And Retrieval

    rtk uv run pytest tests/unit/runtime_lab/test_intent_catalog.py tests/unit/runtime_lab/test_intent_retriever.py tests/unit/runtime_lab/test_mock_semantic_recall.py -q --tb=short
    rtk uv run pytest tests/contract/test_runtime_lab_semantic_evidence_api.py tests/integration/runtime_lab/test_runtime_lab_intent_catalog.py tests/e2e/test_runtime_lab_airline_scale_e2e.py -q --tb=short

Required frozen-set metrics: Recall@5 `>= 0.98`, Macro-F1 `>= 0.95` and not
below Spec 228 baseline, answer snippets in classifier input `0`, external
provider calls `0`, stable catalog content hash.

## 230.1-230.3 Trusted Route Execution Gate

    rtk uv run pytest tests/unit/runtime_lab/test_route_execution_gate.py tests/unit/runtime_lab/test_route_read_gate.py tests/unit/runtime_lab/test_confirmation_receipt.py -q --tb=short
    rtk uv run pytest tests/contract/test_runtime_lab_api.py tests/contract/test_runtime_lab_session_message_gateway_api.py tests/contract/runtime_lab/test_trusted_execution_context.py -q --tb=short
    rtk uv run pytest tests/integration/runtime_lab/test_route_read_answer_gate.py tests/integration/runtime_lab/test_route_execution_mutation_gate.py tests/integration/runtime_lab/test_runtime_lab_service.py tests/integration/runtime_lab/test_runtime_lab_handoff_policy.py -q --tb=short

Required threat families: body/header impersonation, missing permissions,
cross-tenant/session/action receipt, expiry, stale version, parallel duplicate,
idempotent replay, and local-development real-write escalation. FAQ/RAG/
clarify/no-match/safe Agent answers require read permission and prove zero
task/child mutation. The surface contract covers session create, gateway/session
message, stream, task/event, and Chatflow trace endpoints; it explicitly does
not claim route-model connectivity or fallback-agent administration.

## 230.4 Child Runtime V2 Authorization

    rtk uv run pytest tests/contract/runtime/nodes/test_side_effect_idempotency.py tests/contract/runtime/test_idempotency_layers.py tests/contract/runtime/test_runtime_lab_effect_authorization.py -q --tb=short
    rtk uv run pytest tests/integration/workflow/test_runtime_v2_api_call_node.py tests/integration/workflow/test_runtime_v2_tool_call_node.py tests/integration/runtime/test_runtime_lab_side_effect_authorization.py -q --tb=short

Required evidence: missing/tampered authority yields no effect and no success
event; API Call and handoff are external; server metadata distinguishes
read-only from write/unknown Tool Call; nested Workflow/Agent calls cannot
escalate; ordinary Message/Variable Assign stays internal; RuntimeLab owner
opts in; non-RuntimeLab owners preserve accepted behavior. Spec 230 also
requires independent security Checker and a fresh-context Reviewer with no
unresolved Critical/High.

## 231.1-231.3 Composite Intent

    rtk uv run pytest tests/unit/runtime_lab/test_composite_intent_detector.py tests/unit/runtime_lab/test_composite_intent_policy.py -q --tb=short
    rtk uv run pytest tests/contract/test_runtime_lab_semantic_evidence_api.py tests/contract/runtime_lab/test_composite_intent_api.py tests/integration/runtime_lab/test_composite_intent_ledger.py tests/integration/runtime_lab/test_composite_intent_mutation_gate.py -q --tb=short
    rtk uv run pytest tests/e2e/test_runtime_lab_semantic_api_e2e.py tests/e2e/test_runtime_lab_composite_intent_e2e.py tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py -q --tb=short

The refund-plus-invoice regression must preserve both components, ask for
order, and perform zero mutation. Explicit choice re-evaluates the Spec 230
gate. Expired/stale/cross-session plans fail closed; single-intent and
suspend/resume behavior remain green.

## Browser UAT

The owning slices add and run:

    rtk node frontend/e2e/runtime-lab-intent-routing-uat.mjs

The reusable script must cover:

1. low-confidence targeted clarification and idempotent replay;
2. fused candidate evidence, bounded context, and catalog version;
3. permission deny, confirmation, allow, and stale retry;
4. composite order clarification, explicit component choice, and
   consultation-plus-transaction offer;
5. unchanged active/suspended state on every clarify/deny/offer turn.

Store screenshots, browser console/network report, server log, and mutation
evidence under the owning slice. An unavailable browser/server is
`ENV-BLOCKED-BROWSER`, not PASS.

## Program Regression Gate

    rtk uv run pytest tests/unit/runtime_policy tests/unit/runtime_lab -q --tb=short
    rtk uv run pytest tests/contract/test_runtime_policy_profile_api.py tests/contract/test_runtime_policy_replay_api.py tests/contract/test_runtime_policy_release_api.py tests/contract/test_runtime_policy_decision_log_api.py tests/contract/test_runtime_lab_api.py tests/contract/test_runtime_lab_semantic_evidence_api.py tests/contract/test_runtime_lab_session_message_gateway_api.py tests/contract/runtime_lab -q --tb=short
    rtk uv run pytest tests/integration/runtime_lab -q --tb=short
    rtk uv run pytest tests/e2e/test_runtime_lab_api_e2e.py tests/e2e/test_runtime_lab_semantic_api_e2e.py tests/e2e/test_runtime_lab_airline_scale_e2e.py tests/e2e/test_runtime_lab_fallback_matrix_e2e.py tests/e2e/test_runtime_lab_confusion_rag_agent_matrix_e2e.py tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py -q --tb=short
    rtk uv run ruff check app/modules/runtime_lab app/modules/runtime_policy app/modules/runtime
    rtk npm --prefix frontend run test:unit
    rtk npm --prefix frontend run build
    rtk uv run alembic heads
    rtk uv run alembic check
    rtk git diff --check

## Delivery And Secret Gate

    rtk git status --short
    rtk git diff --stat
    rtk git diff --check
    rtk git diff --cached --check
    rtk rg -n "(sk-|api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*['\"][^$<{]" specs/228-runtime-policy-replay-and-uncertainty specs/229-runtime-lab-intent-routing-reliability specs/230-runtime-route-execution-boundary specs/231-runtime-lab-composite-intent docs/adr/0010-runtime-route-decision-and-execution-boundary.md loop

Any plausible credential requires manual inspection. Commit/push only the
active slice. PR, merge, deploy, production migration/application, and live
provider use remain unauthorized.
