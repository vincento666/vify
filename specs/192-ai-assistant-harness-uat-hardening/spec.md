# Spec 192: AI Assistant Harness UAT Hardening

## Goal

Close the production-readiness gaps exposed by complex AI Assistant browser UAT
before the harness is used as the foundation for a customer-assistant copilot.

## Scope

In scope:

- approval decisions must close the run lifecycle: approval resumes the approved
  tool and completion, denial closes the run as denied;
- inspector approval data must distinguish pending approvals from approval
  history;
- live Qwen token usage must flow into inspector usage;
- the AI Assistant shell must expose stable automation/accessibility contracts
  for critical controls;
- sessions must be easier to distinguish from historical test/mock-looking
  records;
- remaining known non-goals, such as real skill execution and true realtime
  streaming, must be explicit in risk/UAT evidence.

Out of scope:

- implementing the customer-assistant copilot window itself;
- replacing event replay with SSE/WebSocket streaming;
- executing local Codex skills from `invoke_skill`;
- touching unrelated dirty `customer_assistant` worktree changes.

## Acceptance Criteria

- RED evidence exists for approval resume/deny closeout, inspector approval
  split, frontend automation/accessibility contracts, and usage propagation.
- Approving `write_workspace_file` executes the approved tool, records a
  tool-call row, emits approval/tool/run events, and completes the run.
- Denying a business write records `approval.denied`, clears pending approval
  queue, stores approval history, and marks the run denied.
- Inspector `approvalQueue` contains only pending approvals and
  `approvalHistory` contains all approvals for the run.
- Live Qwen usage appears in `inspector.usage` and frontend usage display.
- Browser UAT covers read + skill intent + restricted write approval, sandbox
  denial, business-write denial, approval resume, one-screen UI, and cleanup.
