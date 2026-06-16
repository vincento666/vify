# Spec 094: Customer Assistant Task Recognition Evidence Panel

## Goal

Make task recognition evidence visible and auditable in the customer assistant
workbench. When a customer turn is classified into tasks, the operator should
see which task command was recognized and which worker profile/model/prompt/tool
risk policy references were used to route it.

## Acceptance Criteria

- `task_recognized` events include profile references for each recognized
  command when a configured worker profile matches the task key.
- The operator workbench shows a compact recognition evidence panel separate
  from the raw event timeline.
- The evidence panel lists task key, task type, worker route, profile id, model
  policy, prompt, tools, and risk policy without exposing raw customer PII or
  secrets.
- Empty sessions render an explicit empty state.
- Browser UAT verifies the panel after a real customer-assistant turn.

## Non-goals

- Do not change task recognition logic or worker scheduling.
- Do not add new worker profile schema fields.
- Do not replace the raw event timeline.
- Do not run live LLM acceptance in this slice.

## Evidence

Evidence lives under
`artifacts/slices/094-customer-assistant-task-recognition-evidence-panel/094.1/`.
