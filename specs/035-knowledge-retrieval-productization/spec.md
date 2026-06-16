# Spec 035: Knowledge Retrieval Productization

## Goal

Productize the Knowledge module into a mainstream AI platform knowledge-base
lifecycle with configurable retrieval strategies.

Current behavior proves document chunking, pgvector-like retrieval, FAQ CRUD, and
basic retrieval test flows. 035 closes the product gaps found while comparing
the module against Coze Studio and modern enterprise AI platform expectations:

- retrieval must be selectable, not hard-coded;
- keyword, semantic vector, FAQ, and hybrid recall must have explicit contracts;
- hybrid recall must use a deterministic fusion/rerank layer;
- FAQ must enter the same embedding/vector path as document chunks;
- pgvector and Weaviate must sit behind one vector-store adapter boundary;
- the UI must guide business users through lifecycle steps without exposing
  low-level infrastructure terms by default.

## Current Findings

Implemented today:

- knowledge-base CRUD and enabled state;
- document upload/import lifecycle;
- document chunk persistence;
- document vector embedding persistence for pgvector-backed search;
- FAQ CRUD, CSV import/export, enabled flag, and priority;
- retrieval test API and frontend tab;
- Agent retrieval settings for topK, score threshold, rerank flag, and citation
  style.

Gaps:

- retrieval test requests only accept query and topK;
- backend retrieval always runs semantic vector, keyword, and FAQ matching;
- no user-facing or API-facing `semantic` / `keyword` / `hybrid` / `FAQ` mode;
- FAQ retrieval uses exact and token-overlap heuristics, not FAQ embeddings;
- embedding provider is a fake local hash provider, with no OpenRouter/local-HF
  adapter contract;
- rerank flag is stored in Agent settings but ignored by chat runtime;
- hybrid merge is score-sort based, not an explicit RRF/rerank pipeline;
- vector storage is coupled to pgvector repository methods instead of an
  adapter usable by Weaviate;
- UI still presents retrieval as a technical test form rather than a lifecycle
  quality check.

## Product Principles

- Business object first: Knowledge base, Document, FAQ, Chunk, Recall Strategy,
  Quality Test, Publish/Use.
- User task first: create, import, clean, segment, enrich, test, tune, publish,
  observe.
- Progressive disclosure: default labels describe outcomes; advanced settings
  expose technical controls only after expansion.
- Selectable strategy: default can be "smart", but users must be able to choose
  semantic, keyword, hybrid, or FAQ-only retrieval.
- Adapter isolation: embedding provider, vector store, and reranker must be
  replaceable without changing API/router/frontend contracts.
- First replicate, then enhance: 035 introduces production contracts and local
  adapters; deeper live quality tuning can remain opt-in.

## Lifecycle Scope

The mainstream knowledge-base flow must cover:

1. create knowledge base and set business description;
2. import documents and FAQ files;
3. parse and segment source content;
4. generate embeddings for chunks and FAQ rows;
5. index vectors and keyword material;
6. preview segments and FAQ rows;
7. test retrieval with selectable strategy;
8. tune topK, score threshold, rerank, and mode;
9. bind knowledge base to Agent/Chat runtime;
10. observe retrieval references and quality evidence;
11. update/reimport content without losing lifecycle status;
12. disable/archive content from runtime retrieval.

## Retrieval Modes

The API and domain layer must support these modes:

- `auto`: product default; maps to the knowledge base default strategy.
- `hybrid`: run semantic and keyword recall, then fuse and optionally rerank.
- `semantic`: run vector recall only.
- `keyword`: run full-text/keyword recall only.
- `faq`: run FAQ recall only.

FAQ exact matching remains useful, but it must be modeled as one FAQ recall
signal, not the only FAQ strategy. FAQ vector recall must use the embedding
adapter and vector-store adapter.

## Acceptance Criteria

- Retrieval test request accepts mode, topK, score threshold, and rerank.
- KnowledgeFacade accepts explicit retrieval options while preserving the old
  default behavior as `auto` / `hybrid`.
- Semantic mode does not include keyword-only document hits.
- Keyword mode does not call vector-store semantic recall.
- FAQ mode searches FAQ rows only.
- Hybrid mode fuses semantic and keyword candidates through a deterministic
  RRF-compatible strategy.
- Rerank is represented by a domain adapter contract; local RRF works without
  external credentials.
- FAQ embeddings are generated through the same embedding provider abstraction
  as document chunks.
- Vector search is called through an adapter interface with pgvector and
  Weaviate implementations or stubs behind the same contract.
- Agent chat runtime passes retrieval mode/rerank settings into knowledge
  search.
- Frontend retrieval test exposes business-friendly mode choices and hides
  weights/provider/vector-store details behind advanced controls.
- Frontend text must not claim the knowledge module is mock-only after real
  retrieval paths are active.
- REM governance passes for changed frontend files.
- Spec, plan, tasks, and evidence paths are updated before sign-off.

## Out Of Scope

- replacing pgvector as the default local development store;
- requiring live OpenRouter or HuggingFace credentials for ordinary CI;
- full Weaviate deployment automation;
- offline embedding model download in CI;
- production-grade learning-to-rank beyond deterministic local rerank.

## Slices

### 035.1 Retrieval Strategy Contract

Add mode/options schema, domain retrieval options, RRF fusion, retrieval-test API
coverage, and backward-compatible defaults.

### 035.2 Embedding And FAQ Vector Contract

Introduce embedding provider protocol/factory, OpenRouter adapter, local fake
fallback, FAQ embedding persistence contract, and FAQ vector recall tests.

### 035.3 Vector Store Adapter Boundary

Move semantic search behind a vector-store adapter with pgvector default and
Weaviate-compatible implementation boundary.

### 035.4 Product UX Lifecycle

Update Knowledge UI to expose lifecycle steps and retrieval strategy selection
with progressive disclosure and REM-safe styling.

### 035.5 Runtime And Quality Loop

Pass Agent retrieval settings into chat runtime, surface references/strategy
evidence, and record test/UAT artifacts.

## Completion Gate

035 is complete only when:

- every slice has RED, green unit/integration, frontend, and UAT evidence;
- changed docs list completed behavior and remaining live-provider limitations;
- default retrieval remains compatible with existing tests;
- no new frontend bare `px` is introduced outside the allowlist;
- one final audit confirms the lifecycle list above is implemented or tracked
  by a later spec with explicit rationale.

## 035 Completion Sign-off

Status: complete for local productized retrieval path.

Delivered:

- selectable retrieval modes: `auto`, `hybrid`, `semantic`, `keyword`, `faq`;
- retrieval-test API and UI controls for mode, topK, threshold, and rerank;
- deterministic RRF fusion helper for hybrid recall;
- FAQ embedding table, Alembic migration, create/update/import embedding writes,
  and FAQ vector recall;
- OpenRouter embedding adapter with mocked transport tests and fake provider
  fallback for local/CI;
- vector-store adapter boundary with repository/pgvector default and safe
  Weaviate adapter boundary;
- Agent retrieval settings carry mode/rerank/threshold into chat RAG runtime;
- Knowledge UI lifecycle strip and business-friendly retrieval labels.

035.6 follow-up:

- live Weaviate search was verified against local Docker image
  `vifly-experiment-weaviate-1` on `127.0.0.1:8080`;
- `WeaviateVectorStore` now performs GraphQL vector search for document chunks
  and FAQ rows;
- `WeaviateVectorStore` now replaces document and FAQ embeddings through the
  same vector-store adapter contract used by the repository/pgvector path;
- `create_vector_store()` selects Weaviate when configured through
  `HIFY_VECTOR_STORE=weaviate` and `HIFY_WEAVIATE_URL`;
- local HuggingFace-style embedding adapter is available through
  `LocalSentenceTransformerEmbeddingProvider`, `HIFY_EMBEDDING_PROVIDER=local-hf`,
  and `HIFY_LOCAL_EMBEDDING_MODEL`;
- HTTP reranker adapter exists for online/lightweight rerank services and is
  invoked when retrieval `rerank` is enabled, with RRF still available locally.

Remaining caveat:

- live OpenRouter/local-HF embedding generation and live external rerank service
  quality remain opt-in because credentials/model packages are
  environment-dependent.

Final evidence:

- RED/green strategy: `artifacts/slices/035-knowledge-retrieval-productization/035.1/`;
- FAQ vector/provider: `artifacts/slices/035-knowledge-retrieval-productization/035.2/`;
- vector-store adapter: `artifacts/slices/035-knowledge-retrieval-productization/035.3/`;
- frontend UAT: `artifacts/slices/035-knowledge-retrieval-productization/035.4/`;
- final gates and lifecycle audit:
  `artifacts/slices/035-knowledge-retrieval-productization/035.5/`;
- Weaviate/rerank/local-HF adapter follow-up:
  `artifacts/slices/035-knowledge-retrieval-productization/035.6/`.
