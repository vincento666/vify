# Spec 079: MVP Demo Bootstrap Contract

## Goal

Turn the existing MVP demo seed into a productized bootstrap contract: one
operator command should seed the topology, verify the seeded records, write only
non-secret environment bindings, and leave behind enough evidence for browser
UAT scripts to trust the demo data.

## Acceptance Criteria

- `scripts/seed_mvp_demo.py` seeds and verifies the topology in one run.
- The command prints a clear verification pass marker and never prints API keys,
  tokens, or secret-looking values.
- A reusable backend verifier checks:
  - all required demo story IDs exist;
  - customer-assistant sessions are mapped one-to-one to stories;
  - each story has tasks and at least one seeded event;
  - action-backed stories include pending proposed actions;
  - airline SOP Chatflow bindings exist and point at published Chatflows;
  - seeded knowledge FAQ entries are present and keyword-searchable;
  - generated env output is secret-free.
- The verifier output is JSON-friendly so later browser UAT scripts can record
  the topology contract without direct DB inspection.
- The existing seed remains idempotent.

## Non-goals

- Do not add live provider credentials or live LLM calls.
- Do not build a seed administration UI.
- Do not change customer-assistant runtime behavior except to expose verification
  evidence.

## Evidence

Evidence lives under
`artifacts/slices/079-mvp-demo-bootstrap-contract/<slice>/`.
