# Spec 080: Runtime V2 Knowledge Node MVP

## Goal

Extend Chatflow/Workflow runtime v2 with a product-demo-safe `KNOWLEDGE` node
path so seeded knowledge can be used by async runs, node events, and canvas/debug
evidence without falling back to legacy runtime.

## Acceptance Criteria

- Runtime v2 compatibility accepts `KNOWLEDGE` nodes while continuing to reject
  `LLM`, tool, agent, code, and nested workflow nodes.
- A Chatflow v2 run can execute `START -> KNOWLEDGE -> END` and return a real
  FAQ-backed answer from the knowledge facade.
- Runtime v2 emits normal node started/completed/status events for the knowledge
  node, with redacted payloads and node list/debug compatibility.
- Workflow v2 can use the same executor path from a published snapshot.
- Missing or unconfigured knowledge facade behavior remains explicit and does
  not silently pretend to be live retrieval in production-facing service wiring.

## Non-goals

- Do not add runtime v2 `LLM` execution in this slice.
- Do not add live provider credentials.
- Do not implement pgvector or external vector-store requirements beyond the
  repository-backed knowledge facade already present.
- Do not change legacy workflow/chatflow knowledge behavior.

## Evidence

Evidence lives under
`artifacts/slices/080-runtime-v2-knowledge-node-mvp/<slice>/`.
