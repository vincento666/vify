# 073 Demo Seed And Topology Bootstrap

## Goal

Create one repeatable demo bootstrap for the productized MVP. A fresh local or
MySQL8 demo database must be able to run one command and receive the minimum
topology needed for the customer assistant and Chatflow/Workflow demo stories:
provider/model config, airline Chatflow SOP bindings, knowledge material,
customer-assistant sessions, task templates, worker defaults, and named demo
story metadata.

## Acceptance Criteria

- A single command initializes the demo topology without requiring live provider
  credentials.
- The bootstrap is idempotent: running it twice updates or reuses the same demo
  records and does not duplicate providers, models, knowledge, workflows,
  sessions, or story definitions.
- Existing RuntimeLab airline Chatflow seed behavior remains compatible and is
  reused instead of forked.
- The command writes only non-secret local environment bindings. API keys stay
  in shell/provider config and never appear in generated files, stdout evidence,
  or artifacts.
- The seed creates at least three named demo stories:
  - refund + baggage allowance in parallel;
  - invoice request interrupted by flight status;
  - Chatflow information collection that blocks, resumes, and produces an
    operator recommendation.
- The seeded customer-assistant data includes at least two customer sessions,
  realistic task ledgers, proposed-action examples, worker configuration
  defaults, and knowledge/advisory bindings.
- The seeded knowledge data is sufficient for deterministic operator-advisory
  and browser UAT checks without live RAG.
- MySQL8 compatibility is preserved for seed writes and JSON payloads.
- Browser UAT can load the customer assistant, RuntimeLab/Chatflow, and
  evaluation/observe surfaces from the seeded topology.

## Evidence

- RED:
  `artifacts/slices/073-demo-seed-and-topology-bootstrap/073.1/red.txt`
- Unit:
  `artifacts/slices/073-demo-seed-and-topology-bootstrap/073.1/unit.txt`
- Integration / MySQL8 compatibility:
  `artifacts/slices/073-demo-seed-and-topology-bootstrap/073.1/integration.txt`
- E2E:
  `artifacts/slices/073-demo-seed-and-topology-bootstrap/073.1/e2e.txt`
- Browser UAT:
  `artifacts/slices/073-demo-seed-and-topology-bootstrap/073.1/uat.md`

## Non-goals

- Do not introduce real paid provider calls in the default seed.
- Do not implement the full worker-profile admin UI; 075 owns configurable
  worker/skill productization.
- Do not add broad auth/RBAC behavior; 077 owns demo auth and redaction
  boundaries.
