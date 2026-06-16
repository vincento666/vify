# Plan 035: Knowledge Retrieval Productization

## Architecture

```text
Knowledge UI
  -> retrieval test request
  -> Knowledge web schemas
  -> KnowledgeFacade.search_context(options)
  -> RetrievalStrategy
     -> KeywordRetriever
     -> VectorStoreAdapter
        -> PgvectorVectorStore
        -> WeaviateVectorStore
     -> FaqRetriever
     -> Reranker/RRF
  -> ContextResult[]
```

The existing repository remains the persistence owner. 035 adds adapter seams at
the semantic-search, embedding, and rerank boundaries so product behavior no
longer depends on pgvector-specific repository calls or fake hash embeddings.

## Retrieval Contract

Use a single domain options object:

```text
mode: auto | hybrid | semantic | keyword | faq
top_k: int
min_score: float
rerank: bool
```

Default `auto` maps to `hybrid` for compatibility with today's always-combined
behavior. Existing callers that pass only `top_k` keep working.

## Hybrid Fusion

Local deterministic fusion uses Reciprocal Rank Fusion:

```text
score = sum(weight / (rank_constant + rank))
```

RRF is credential-free, stable, and matches the class of retrieval design used
by Coze Studio. External HTTP rerankers are available behind the same adapter
when `rerank` is enabled.

## Embedding Providers

Provider order:

1. configured OpenRouter embedding model when API key/model are present;
2. configured local embedding adapter when available;
3. fake deterministic embedding only for tests/local fallback.

OpenRouter and local-HF adapters are not required for ordinary CI to make live
network calls. They must expose payload/response contracts and skip/fallback
cleanly when credentials or model files are absent.

035.6 current model scan:

- OpenRouter embeddings endpoint currently lists
  `nvidia/llama-nemotron-embed-vl-1b-v2:free` as a zero-priced embedding model.
- Cheap lightweight candidates include
  `perplexity/pplx-embed-v1-0.6b`,
  `sentence-transformers/paraphrase-minilm-l6-v2`,
  `sentence-transformers/all-minilm-l12-v2`,
  `baai/bge-base-en-v1.5`, and `intfloat/e5-base-v2`.
- Local fallback adapter defaults to
  `sentence-transformers/all-MiniLM-L6-v2` when
  `HIFY_EMBEDDING_PROVIDER=local-hf`.

Config examples:

```text
HIFY_EMBEDDING_PROVIDER=openrouter
OPENROUTER_API_KEY=...
HIFY_OPENROUTER_EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free

HIFY_EMBEDDING_PROVIDER=local-hf
HIFY_LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Vector Stores

Pgvector remains default. Weaviate is introduced behind the same adapter
contract:

```text
search_chunks(kb_id, query_embedding, top_k, min_score)
search_faqs(kb_id, query_embedding, top_k, min_score)
replace_document_embeddings(...)
replace_faq_embeddings(...)
```

Tests can use fake/in-memory adapters; integration tests continue using the
existing repository-backed path.

035.6 live smoke verified local Weaviate Docker at:

```text
HIFY_VECTOR_STORE=weaviate
HIFY_WEAVIATE_URL=http://127.0.0.1:8080
```

## Frontend UX

Use outcome labels:

- 智能推荐 -> `auto`
- 综合召回 -> `hybrid`
- 语义理解 -> `semantic`
- 关键词匹配 -> `keyword`
- 仅问答库 -> `faq`

Default view shows only query, mode, and result count. Advanced controls expose
score threshold and rerank. Provider/model/vector-store terms stay out of the
default user path.

## Evidence Plan

Use:

```text
artifacts/slices/035-knowledge-retrieval-productization/
  035.1/
  035.2/
  035.3/
  035.4/
  035.5/
```

Each slice records:

- RED output;
- targeted backend unit/integration output;
- targeted frontend output if changed;
- REM output if frontend visual files changed;
- browser UAT notes for visible UX changes.

## Risks

- Existing knowledge files are already dirty. Keep edits scoped and avoid
  reverting user changes.
- Docker access may be unavailable in the current shell even if Weaviate is
  deployed elsewhere. Do not make local CI depend on Docker.
- Live OpenRouter model availability changes. Tests must mock transport and keep
  live acceptance opt-in.
- FAQ vector persistence can require schema migration. First slice should
  establish contracts before broad migration edits.
