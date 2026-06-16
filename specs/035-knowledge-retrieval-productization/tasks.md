# Tasks 035: Knowledge Retrieval Productization

## 035.0 Audit And Spec

- [x] Audit current Knowledge backend, frontend, tests, and specs.
- [x] Confirm current retrieval is hard-coded hybrid-like behavior.
- [x] Confirm FAQ retrieval is not true embedding/vector retrieval.
- [x] Check current OpenRouter embedding model availability.
- [x] Create `spec.md`, `plan.md`, and `tasks.md`.

## 035.1 Retrieval Strategy Contract

- [x] RED: unit test fails until retrieval mode/options exist.
- [x] RED: integration test fails until retrieval-test API accepts mode.
- [x] Implement `RetrievalOptions` and mode normalization.
- [x] Implement deterministic RRF fusion helper.
- [x] Route `semantic`, `keyword`, `hybrid`, `faq`, and `auto` through distinct
  recall paths.
- [x] Preserve old callers as `auto`/`hybrid`.
- [x] Save evidence under
  `artifacts/slices/035-knowledge-retrieval-productization/035.1/`.

## 035.2 Embedding And FAQ Vector Contract

- [x] RED: test fails until embedding provider protocol/factory exists.
- [x] RED: test fails until FAQ vector recall adapter exists.
- [x] Add OpenRouter embedding adapter with mocked transport tests.
- [x] Keep fake deterministic provider for local tests.
- [x] Add FAQ embedding generation/upsert contract.
- [x] Add FAQ vector recall path behind vector-store adapter.
- [x] Save evidence under
  `artifacts/slices/035-knowledge-retrieval-productization/035.2/`.

## 035.3 Vector Store Adapter Boundary

- [x] RED: test fails until semantic retrieval uses vector-store adapter.
- [x] Add pgvector adapter over existing repository methods.
- [x] Add Weaviate adapter boundary with safe no-credentials/no-server behavior.
- [x] Keep Docker/Weaviate live acceptance opt-in.
- [x] Save evidence under
  `artifacts/slices/035-knowledge-retrieval-productization/035.3/`.

## 035.4 Product UX Lifecycle

- [x] RED: frontend test fails until retrieval mode appears in request/model.
- [x] Add business-friendly retrieval mode selector.
- [x] Add progressive advanced controls for score threshold/rerank.
- [x] Remove mock-only wording from active retrieval UI.
- [x] Remove RAG/vector/token technical wording from the main Knowledge UI path.
- [x] Add lifecycle status/checklist where missing.
- [x] Run REM governance and full frontend unit gate.
- [x] Save browser UAT notes and screenshots.

## 035.5 Runtime And Quality Loop

- [x] RED: chat runtime test fails until Agent retrieval mode/rerank affects
  knowledge search.
- [x] Pass Agent retrieval settings into `KnowledgeFacade.search_context`.
- [x] Pass Workflow knowledge-node and LLM knowledge-resource retrieval settings
  into `KnowledgeFacade.search_chunks`.
- [x] Surface retrieval strategy evidence in references/test output.
- [x] Run targeted chat/knowledge integration gates.
- [x] Run final product lifecycle audit against `spec.md` lifecycle list.
- [x] Save final evidence and completion sign-off.

## 035.6 Weaviate, local embedding, and rerank adapter follow-up

- [x] RED: tests fail until Weaviate HTTP search, local-HF embedding provider,
  reranker adapter, and vector-store factory exist.
- [x] Implement Weaviate GraphQL adapter for document chunks and FAQ rows.
- [x] Implement Weaviate document/FAQ embedding replacement write path.
- [x] Implement `create_vector_store()` with Weaviate config support.
- [x] Implement local sentence-transformers embedding adapter.
- [x] Support `HIFY_LOCAL_EMBEDDING_MODEL` for local-HF model selection.
- [x] Implement RRF and HTTP reranker adapter contracts.
- [x] Invoke configured reranker when retrieval `rerank` is enabled.
- [x] Wire KnowledgeBaseService and KnowledgeFacade through embedding and
  vector-store factories.
- [x] Run local Weaviate Docker smoke against `127.0.0.1:8080`.
- [x] Save RED/GREEN/live-smoke evidence under
  `artifacts/slices/035-knowledge-retrieval-productization/035.6/`.
