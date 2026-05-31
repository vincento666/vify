# ADR 0001: Python FastAPI Shell Migration

## Status

Accepted

## Context

The source project is a Spring Boot 3.2.3 modular monolith with MyBatis-Plus,
OkHttp, Resilience4j, Redis, MySQL, and planned pgvector integration. The target
runtime is Python 3.12 with FastAPI and SQLAlchemy 2.0.

The existing product boundary includes provider management, agent management,
chat streaming, knowledge mock/RAG planning, workflow orchestration, and MCP
server integration. Some current features are mock or partial: knowledge chunks
are in memory, MySQL schema is behind H2 schema, and tool calling is not fully
wired in the OpenAI adapter.

## Decision

We will rebuild the backend as a Python/FastAPI modular monolith and preserve the
existing frontend API contract first. Real RAG and real tool/MCP improvements are
deferred until after the replica features pass acceptance gates.

## Drivers

- Keep migration risk bounded by preserving current product behavior.
- Use Python 3.12 stable ecosystem for FastAPI, SQLAlchemy, Pydantic, Alembic,
  httpx, Redis, and pgvector.
- Avoid a direct line-by-line Java translation that would copy Spring and
  MyBatis assumptions into Python.
- Make missing behavior visible through specs and red tests before implementing.

## Alternatives Considered

1. **Direct Java-to-Python translation**
   - Rejected because it would preserve current coupling and obscure runtime
     differences around async streaming, dependency injection, and transactions.
2. **Big-bang real implementation**
   - Rejected because current RAG and tool calling are partial. Replacing mocks
     while changing language would multiply risk.
3. **Incremental replica slices**
   - Chosen because it matches the original 0-to-1 project order and gives each
     feature a testable delivery boundary.

## Consequences

- The project will temporarily have detailed specs before production code.
- Each slice has overhead from RED evidence, E2E, and browser UAT.
- Migration velocity is slower at first, but later implementation should be less
  ambiguous.

## Follow-ups

- Create `000-current-boundary-inventory`.
- Reconcile MySQL and H2 schemas before Alembic baseline.
- Build specs `001` through `010` with slice-level gates.
