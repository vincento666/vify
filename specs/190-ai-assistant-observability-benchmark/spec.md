# Spec 190: AI Assistant Token And Cost Usage

## Status

Slices 190.0 and 190.1 remain historical completed observability-tracer work.
No further benchmark work is planned.

Current implementation starts at 190.3 and is limited to real token/cost
accounting plus a user-facing usage dashboard.

## Goal

Record one immutable usage row per AI Assistant model call, then expose scoped
session/total aggregates and a mainstream token-usage dashboard:

    model call usage
      -> scoped immutable ledger
      -> versioned cost resolution
      -> daily/session/dimension aggregates
      -> Token / Cost dashboard

## Scope

In scope:

- current trusted user and current workspace only;
- raw granularity: one row per model invocation;
- aggregation by session and total;
- common dimensions: date, session, provider, model, token type;
- token dimensions include input, output, cache read, cache write, reasoning,
  and total;
- actual or versioned-estimated USD cost;
- summary cards, daily heatmap, session details/ranking, provider/model
  distribution, and token composition;
- Token/Cost toggle and time-range filter;
- backend APIs plus frontend route and Browser UAT.

Out of scope:

- benchmark suites or pass/fail scoring;
- governance policy, budget enforcement, alerts, anomaly detection, SLO, quota,
  billing, invoice, or chargeback;
- cross-user/admin overview;
- customer-assistant, workflow, chatflow, or provider-wide usage dashboards;
- retroactive price recalculation.

## Isolation

Every ledger row and query is keyed by:

    user_id
    workspace_id

Identity follows Spec 188 trusted scope resolution. The client may select time
range and display mode, but cannot query arbitrary user/workspace identifiers.
Session IDs must be proven to belong to the current scope before aggregation or
detail access.

## Canonical Usage Ledger

Minimum row:

    id
    user_id
    workspace_id
    session_id
    run_id
    call_id
    call_kind
    provider
    model
    input_tokens
    output_tokens
    cache_read_tokens
    cache_write_tokens
    reasoning_tokens
    total_tokens
    usage_source
    provider_cost_usd
    estimated_cost_usd
    effective_cost_usd
    cost_source
    pricing_version
    started_at
    completed_at

Rules:

- UNIQUE(user_id, workspace_id, run_id, call_id) identifies one invocation;
- one streaming request is one call and receives a narrowly defined completion
  update when final provider usage arrives;
- rows are immutable except a narrowly defined completion update for a call
  initially recorded before provider usage arrives;
- token fields are non-negative; unavailable optional dimensions are null, not
  invented as zero;
- total_tokens uses provider total when present; otherwise it is input plus
  output unless a provider normalizer explicitly defines other non-overlapping
  semantics;
- cache and reasoning values are breakouts and are never blindly added to total;
- canonical ledger does not use word-count token estimates;
- normal planner calls and Spec 188 memory-extractor calls are both model calls
  and must be recorded;
- a memory-extractor call is attributed to the third run/session that triggered
  its batch;
- provider usage/cost is recorded even when the enclosing run later fails;
- duplicate delivery/replay cannot double-count a call;
- all DB changes require Alembic migration and MySQL8 contract/integration
  proof.

## Cost Resolution

Priority:

1. Provider-reported actual cost.
2. Versioned provider/model price table applied to token dimensions.
3. Unknown cost.

Rules:

- USD values use fixed-precision decimal storage and calculation;
- estimated cost records pricing_version and cost_source=price_table;
- provider cost records cost_source=provider;
- missing price records cost_source=unknown and null cost; UI displays
  价格未知, never zero;
- existing rows retain their pricing version and effective cost; later price
  changes do not rewrite history;
- remove the current simplistic totalTokens multiplied by a constant from
  canonical cost displays.

## Aggregate API

All endpoints preserve the existing {code, message, data} envelope.

Allowed additions:

    GET /api/v1/ai-assistant/usage/summary
    GET /api/v1/ai-assistant/usage/daily
    GET /api/v1/ai-assistant/usage/sessions
    GET /api/v1/ai-assistant/usage/dimensions
    GET /api/v1/ai-assistant/usage/sessions/{session_id}

Common query:

    from
    to
    timezone

The server validates range limits and uses trusted workspace timezone by
default.

Required projections:

- today, yesterday, rolling 30 days, and cumulative totals;
- session counts for each summary period;
- daily token/cost buckets for the most recent 12 months by default;
- session totals and per-call detail;
- provider and model totals;
- input/output/cache/reasoning composition;
- explicit unknown-cost count and token total.

## Frontend Dashboard

Route:

    /ai-assistant/usage

Entry: AI Assistant Token 用量 detail action. This spec does not create a
global admin/settings shell.

Required UI:

- cards: today, yesterday, 30 days, cumulative;
- each card: token total, cost or mixed/unknown state, session count;
- daily heatmap similar to the accepted reference image; intensity follows
  selected Token or Cost metric;
- time range defaults to 30 days for detail charts; heatmap defaults to recent
  12 months;
- session ranking/table opens per-session call detail;
- provider/model distribution;
- token-type composition;
- Token/Cost toggle;
- loading, empty, partial-cost, unknown-price, and API-error states;
- no false zero cost when price is unknown.

## Compatibility

- existing run inspector usage stays available;
- inspector values and ledger values must reconcile for the same model calls;
- existing observability snapshot may remain but benchmark data is historical
  and receives no expansion;
- response envelope, scheduler, approval, ToolRunner, and event semantics remain
  compatible.

## Acceptance Criteria

- RED proves one ledger row per call and idempotent replay.
- RED proves user/workspace/session isolation for every usage endpoint.
- MySQL8 tests prove per-call persistence for normal planner and memory
  extractor calls.
- Provider actual cost wins; versioned estimate is stable; unknown price is
  null and visible.
- Session and total aggregates reconcile exactly with ledger fixtures.
- Daily bucketing is timezone-correct at date boundaries.
- Dashboard renders all required cards, heatmap, dimensions, toggle, filters,
  details, and unknown states.
- Existing inspector usage reconciles with ledger totals.
- Frontend unit/contract tests, rem gate, repeatable Browser UAT, backend
  contract/E2E, migration, lint/type, Checker, and Reviewer evidence pass.
- No benchmark/governance/alert/budget/customer-assistant scope is added.
