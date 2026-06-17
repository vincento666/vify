# Spec 183: Final OpenRouter Live Gate Revalidation

## Status

Completed.

## Goal

Refresh the real-provider MVP live LLM evidence on the current branch using
OpenRouter `qwen/qwen3.5-9b`, after the MySQL8, backend non-live,
frontend canvas, and demo UAT gates have converged.

## Functional Requirements

- Run the customer-assistant live ReAct/proposed_action acceptance gate.
- Run Runtime Lab live Chatflow LLM SOP acceptance.
- Run Runtime Lab OpenRouter full-chain acceptance.
- Run runtime v2 Workflow live LLM node acceptance.
- Run product chat live paths.
- Run base OpenRouter chat/tool-call acceptance.
- Use disposable MySQL8 databases for gates that persist providers, models,
  workflows, chatflows, tasks, or runs.
- Save outputs under
  `artifacts/slices/183-final-openrouter-live-gate-revalidation/183.1/`.

## Non-Goals

- Do not store provider credentials in tracked files, specs, artifacts, or
  seeded database rows beyond transient disposable test databases.
- Do not broaden the live model matrix beyond the requested Qwen 3.5 9B
  target in this slice.
- Do not weaken acceptance assertions or convert live failures into hidden
  skips.

## Acceptance Criteria

- Customer-assistant live gate passes with task recognition, recommendation,
  ReAct tool-call, and proposed_action safety categories.
- Runtime Lab live Chatflow SOP gate passes.
- Runtime Lab OpenRouter full-chain gate passes.
- Runtime v2 Workflow live LLM node gate passes.
- Product chat live paths pass.
- Base OpenRouter chat/tool-call acceptance passes.
- Artifact scan finds no OpenRouter API key material.

## Evidence

- RED: `artifacts/slices/183-final-openrouter-live-gate-revalidation/183.1/resume-data-red.txt`
  captured the missing current-turn slot merge in Chatflow resume data.
- Unit/focused: `resume-data-green.txt`, `runtime-lab-chatflow-focused-final.txt`,
  `customer-assistant-live-react-local-compatible.txt`, and `ruff-final.txt` passed.
- Live qwen gates: `runtime-v2-openrouter-qwen.txt`,
  `runtime-lab-live-chatflow-llm-sop-qwen.txt`,
  `runtime-lab-openrouter-full-chain-qwen.txt`,
  `openrouter-llm-tool-call-qwen.txt`,
  `openrouter-product-chat-paths-qwen.txt`, and
  `customer-assistant-live-react-qwen.txt` passed.
- Artifact scan: `artifact-scan.txt` is empty for OpenRouter key, SQLite URL,
  and `hify-uat.db` markers.
