# Plan 190: AI Assistant Token And Cost Usage

## Architecture

Add:

    domain/usage.py
      provider usage normalization
      versioned cost resolver
      aggregate DTOs

    infra/schema.py + Alembic
      immutable ai_assistant_model_usage ledger
      versioned price definitions or versioned config snapshot

    infra/repository.py
      idempotent per-call insert/completion
      scoped aggregate queries

    web/router.py + schemas.py
      summary, daily, sessions, dimensions, detail

    frontend
      /ai-assistant/usage dashboard
      API client and typed view models

All queries apply trusted user/workspace scope before caller-supplied filters.

## Slice Order

### 190.3 Per-Call Usage Ledger

Build:

- Alembic migration and MySQL8 table;
- normalized provider usage DTO;
- unique scoped call identity;
- planner model-call capture;
- memory-extractor capture when Spec 188.6 is present;
- nullable optional token dimensions;
- immutable/idempotent repository writes.

RED/gates:

- provider field normalization;
- streaming finalization and failed enclosing runs;
- cache/reasoning breakout without total double-count;
- duplicate call/replay;
- failed/partial provider response;
- scope ownership;
- MySQL8 migration, integration, contract, lint/type, and regression gates.

### 190.4 Versioned Cost And Aggregate API

Build:

- fixed-decimal actual/estimated/unknown cost resolver;
- immutable pricing version;
- scoped summary, daily, session, dimension, and session-detail endpoints;
- timezone-aware date buckets;
- range validation and unknown-cost projections.

RED/gates:

- provider actual cost precedence;
- historical price stability;
- unknown price is null, not zero;
- ledger-to-session/total reconciliation;
- timezone boundary and cross-scope denial;
- API envelope and pagination/limit compatibility.

### 190.5 Token/Cost Dashboard

Build:

- /ai-assistant/usage route and AI Assistant entry;
- four summary cards;
- recent-year daily heatmap;
- Token/Cost toggle and range filter;
- session ranking/detail;
- provider/model distribution;
- token-type composition;
- loading, empty, partial, unknown, and error states.

RED/gates:

- frontend view-model and component tests first;
- router/navigation tests;
- API contract fixture tests;
- remScaleClosure and full relevant frontend tests;
- repeatable Browser UAT with screenshots and DOM evidence.

### 190.6 Aggregate Acceptance

- reconcile ledger, APIs, inspector, and dashboard fixtures;
- rerun backend/frontend/migration/security gates;
- prove normal planner and memory extractor capture;
- prove no benchmark, governance, alert, budget, or cross-user surface;
- save Checker and Reviewer reports.

## Cross-Spec Execution Order

Recommended order:

1. 188.4 scope/store.
2. 188.5 session scope and prompt cutover.
3. 190.3 usage ledger and generic model-call sink.
4. 188.6 extractor wired through that sink.
5. 188.7 aggregate acceptance.
6. 190.4 aggregate APIs.
7. 190.5 dashboard.
8. 190.6 aggregate acceptance.

This avoids shipping an unaccounted memory-extractor model call.

## Evidence

Evidence root:

    artifacts/slices/190-ai-assistant-observability-benchmark/<slice>/

Recommended backend targets:

    tests/unit/ai_assistant/test_model_usage.py
    tests/integration/ai_assistant/test_model_usage_repository.py
    tests/contract/test_ai_assistant_usage_api.py
    tests/e2e/test_ai_assistant_usage_e2e.py

Recommended frontend targets:

    frontend/src/views/aiAssistant/aiAssistantUsage*.test.ts
    frontend/src/router/ai-assistant-routes.test.ts
    frontend/e2e/ai-assistant-usage-uat.mjs

Names may change; contracted behavior may not.

## TDD And Gates

Each slice:

1. tdd capability preflight and skill invocation;
2. observable RED;
3. minimal GREEN and refactor;
4. applicable Unit, MySQL8 Integration/Contract, E2E, frontend, Browser UAT,
   rem, migration, lint/type, diff checks;
5. Checker, Reviewer, isolated slice commit.

Stop and return to Open Loop if:

- provider pricing units cannot be expressed without a new product decision;
- trusted user/workspace scope from Spec 188 is unavailable;
- canonical recording requires changing non-AI-Assistant products;
- dashboard requires a new global settings/admin information architecture;
- billing, budget enforcement, or cross-user administration is requested.
