# 075 Configurable Worker Skill Profiles

## Goal

Move customer-assistant task routing from engineering-only constants toward a
demo-ready worker profile catalog. The MVP operator should be able to see which
task key/type routes to which worker/chatflow/workflow/react worker, and seeded
or environment configuration should be able to override model, prompt, tools,
and risk policy metadata without editing code.

## Acceptance Criteria

- Customer-assistant runtime exposes worker profile metadata through
  `/api/v1/customer-assistant/worker-profiles`.
- The deterministic task recognizer resolves task commands from the active
  profile catalog instead of hard-coded worker fields.
- The 073 demo seed writes a non-secret worker profile configuration into the
  generated demo env.
- Profile metadata includes task key, task type, worker type/ref, model policy,
  prompt ref, tools, and risk policy.
- Existing default behavior remains compatible when no override is configured.

## Slices

### 075.1 Backend Catalog And Routing Override

Add domain worker profile catalog parsing/defaults, route it through service
construction, expose it via API, and prove task recognition uses an override.

### 075.2 Workbench Profile Visibility

Show active profile metadata in the customer-assistant workbench and browser UAT.

### 075.3 Profile Evaluation Gate

Add acceptance checks that worker profile changes are visible in eval/observe
records and do not weaken proposed-action safety.

## Evidence

Evidence lives under
`artifacts/slices/075-configurable-worker-skill-profiles/<slice>/`.

## Non-goals

- A full admin CRUD UI is not required in 075.1.
- Real tool-calling and real MCP enhancement remain owned by later slices.
