# 106 One-Click Demo Seed

## Goal

Productize the MVP demo seed into a repeatable one-command setup for customer
assistant + Chatflow/Workflow runtime demos. The command must seed the existing
demo topology, add mock-safe provider/model anchors, write non-secret local
environment bindings, and emit a stable JSON report that downstream UAT can use
without direct database inspection.

## Acceptance Criteria

- One command initializes and verifies the MVP demo seed without live LLM
  credentials.
- Running the command twice reuses or updates the same demo provider, model
  config, Chatflow SOP bindings, knowledge base, customer sessions, tasks, and
  proposed actions.
- The generated env file contains only non-secret demo bindings and must not
  include API keys, tokens, passwords, or secret-looking values.
- The seed creates a mock-safe provider/model config pair for demo references
  and future opt-in live upgrade work without changing runtime-v2 or Runtime
  Lab adapter behavior.
- The command writes a JSON report with schema version, seed identifiers,
  topology verification, and enough story/provider/model evidence for Browser
  UAT scripts.
- Existing `073` and `079` demo bootstrap contracts remain green.

## Non-goals

- Do not make live provider calls or require API credentials.
- Do not touch RuntimeLab adapter internals, runtime v2 core, or customer
  assistant UI files.
- Do not implement a full seed admin UI or replace the existing 073 topology
  seed.

## Evidence

- RED: `artifacts/slices/106-one-click-demo-seed/106.1/red.txt`
- Integration: `artifacts/slices/106-one-click-demo-seed/106.1/integration.txt`
- Command: `artifacts/slices/106-one-click-demo-seed/106.1/command.txt`
- Docs: `artifacts/slices/106-one-click-demo-seed/106.1/docs.txt`
