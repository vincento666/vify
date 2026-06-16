# Plan 080

## 080.1 Chatflow V2 Knowledge Tracer Bullet

- Add a RED public-API integration test that creates a knowledge base/FAQ,
  creates a Chatflow with `START -> KNOWLEDGE -> END`, runs `/runs-v2`, and
  expects the FAQ answer plus runtime node evidence.
- Add `KNOWLEDGE` to runtime v2 compatibility and dispatch to
  `KnowledgeNodeExecutor`.
- Thread `KnowledgeFacade` into Chatflow runtime v2 service construction,
  including background completion.
- Run focused integration and lint gates, then save evidence.

## 080.2 Workflow V2 Published Knowledge Snapshot

- Add a RED public-API integration test for a published Workflow v2 snapshot
  using `KNOWLEDGE`.
- Reuse the same runtime v2 executor wiring for Workflow v2 background runs.
- Verify debug/node evidence through existing runtime result/node APIs.

## Gates

- RED before implementation for each slice.
- Focused workflow integration tests.
- Runtime v2 unit compatibility tests.
- Browser UAT when a canvas/debug visible path is changed.
- Docs and artifacts updated per slice.
