# Spec 019: Human Handoff, Channels, Publish, And Observe

## Goal

Turn Workflow and Chatflow from an authoring/runtime MVP into a commercial customer service foundation: Chatflow can transfer a conversation to a human queue, published flows can be exposed through supported channels, and operators can observe runs, sessions, handoffs, and failures.

## Product Boundary

- Starts after 017 resource calls and 018 Chatflow session/resume pass.
- Implements a Chatflow-specific transfer-to-human node distinct from 015 HUMAN_INPUT.
- Provides channel adapter contracts and first runnable channels for Web/API. Third-party channels can have config shells, but are not considered complete until credentials, webhook verification, and message adapters are implemented.
- Adds versioned publish/open/observe behavior for Workflow and Chatflow.
- Does not build a full omnichannel agent desktop, workforce management system, or external CRM integration unless represented as 017 tools.
- Does not implement Dify-style cross-flow task stack.

## Commercial Customer Service Value

A production客服 system needs a safe escape hatch to human service, controlled publishing, channel-specific variables, and operational visibility. Without these, the bot may work in tests but cannot be trusted in customer-facing support.

## Handoff Boundary

### HUMAN_INPUT vs TRANSFER_TO_HUMAN

- `HUMAN_INPUT` from 015 is a generic manual input or approval pause inside a flow.
- `TRANSFER_TO_HUMAN` is Chatflow-only and transfers the live conversation to a human service queue.
- `TRANSFER_TO_HUMAN` pauses or ends bot automation for that conversation according to handoff policy.
- `TRANSFER_TO_HUMAN` creates a handoff ticket with transcript, context, priority, queue, and SLA metadata.

## Node Contract: TRANSFER_TO_HUMAN

- Scope: Chatflow only.
- User-facing label: `转人工`.
- Config fields:
  - handoff message to user.
  - queue or team selector.
  - reason/category mapping.
  - priority mapping.
  - context fields to include: variables, last messages, node outputs, user/channel metadata.
  - SLA target.
  - fallback behavior when no agent/queue is available.
  - after-handoff behavior: end bot run, pause until closed, or resume after human closes.
- Runtime:
  - Creates a handoff ticket.
  - Emits `message` and `handoff_requested` events.
  - Stores transcript/context snapshot.
  - Moves session status to `handoff` or `waiting_human`.
  - Blocks further bot automation until policy allows resume.
- Output:
  - `handoff_id`
  - `handoff_status`
  - `queue`
  - `assignee`
  - `reason`
  - `priority`

## Handoff Ticket Model

Tracks:

- `handoff_id`
- `session_id`
- `conversation_id`
- `user_id`
- `channel`
- `queue`
- `assignee`
- `status`: requested, queued, assigned, in_progress, resolved, returned_to_bot, closed, failed
- `reason`
- `priority`
- `sla_due_at`
- `transcript_snapshot`
- `context_snapshot`
- `created_at`, `updated_at`, `closed_at`

## Channel Boundary

Runnable MVP channels:

- REST API channel for server-to-server invocation.
- Web channel for embedded or hosted web chat preview.

Later-stage or shell-only channels until separately implemented:

- Feishu.
- DingTalk.
- WeCom.
- WeChat Official Account/Mini Program.
- Other enterprise channels.

Channel adapter contract:

- inbound raw message -> internal `AgentRequest`.
- internal events -> channel message format.
- channel identity -> `sys.channel`, `sys.channel_id`, `sys.conversation_id`, `sys.user_id`.
- file attachments -> `sys.files`.
- delivery status and errors -> observe events.

## Publish Contract

Workflow publish:

- Creates immutable published version.
- Exposes Open API execution endpoint.
- Allows rollback to previous published version.
- Records publish metadata and validation result.

Chatflow publish:

- Creates immutable published version.
- Assigns version to one or more channels.
- Supports test channel and production channel separation.
- Validates required channel config and missing resources.
- Records publish metadata, channel config, and active version.

Publish validation checks:

- graph validity.
- no unsupported runnable nodes.
- required provider/model/resource health.
- channel config completeness.
- handoff queue availability when TRANSFER_TO_HUMAN is used.
- secrets are referenced, not stored in graph.

## Observe Contract

Observe surfaces:

- run list with status, duration, channel, user, flow type, version.
- conversation session list for Chatflow.
- node trace detail with input/output/resource calls.
- event timeline including message, interrupt, resume, tool_call, handoff, error.
- handoff ticket list and status.
- aggregate metrics:
  - run count.
  - success/failure rate.
  - latency.
  - token/cost when available.
  - tool call count and failures.
  - handoff rate.
  - containment rate.
  - channel distribution.

## API Surface

MVP endpoints:

- publish:
  - `POST /api/v1/workflows/{workflow_id}/publish`
  - `POST /api/v1/chatflows/{chatflow_id}/publish`
  - `GET /api/v1/workflows/{workflow_id}/versions`
  - `GET /api/v1/chatflows/{chatflow_id}/versions`
- channels:
  - `GET /api/v1/chatflows/{chatflow_id}/channels`
  - `PUT /api/v1/chatflows/{chatflow_id}/channels/{channel_id}`
  - `POST /api/v1/chatflows/{chatflow_id}/channels/{channel_id}/test`
- handoff:
  - `GET /api/v1/handoffs`
  - `GET /api/v1/handoffs/{handoff_id}`
  - `POST /api/v1/handoffs/{handoff_id}/assign`
  - `POST /api/v1/handoffs/{handoff_id}/close`
  - `POST /api/v1/handoffs/{handoff_id}/return-to-bot`
- observe:
  - `GET /api/v1/observe/runs`
  - `GET /api/v1/observe/runs/{run_id}`
  - `GET /api/v1/observe/sessions`
  - `GET /api/v1/observe/metrics`

Endpoint naming can be adjusted to existing router conventions, but the behavior must remain testable.

## Frontend Behavior

- Chatflow add-node palette exposes `转人工` after runtime exists.
- Right panel for `转人工` uses Coze-like section layout:
  - queue and policy.
  - message to user.
  - context snapshot fields.
  - fallback/after-handoff.
  - advanced SLA/audit.
- Publish modal validates graph, resources, channel config, and handoff queue.
- Channel tab shows Web/API runnable channels and disabled third-party shells.
- Observe tab shows run/session/handoff lists and trace details without embedding a tiny canvas.
- Debug dock links run events to observe details.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 019.1 TRANSFER_TO_HUMAN node and ticket model | Chatflow can create handoff ticket and pause/end bot automation | RED: handoff node tests fail; Unit: ticket service; Integration: session status; E2E: transfer node run; UAT: ticket visible |
| 019.2 Channel adapter contract and Web/API channels | Published Chatflow can run through API/Web channel profile | RED: channel contract tests fail; Unit: adapters; Integration: channel invocation; E2E: web/api preview |
| 019.3 Versioned publish and rollback | Workflow/Chatflow publish immutable versions with validation | RED: publish version tests fail; Integration: active version and rollback; E2E: publish guard |
| 019.4 Observe surfaces | Runs, sessions, node traces, events, and handoffs are queryable and visible | RED: observe tests fail; Integration: filters; E2E: observe route |
| 019.5 Ops/security polish | Audit, permissions placeholders, sanitized logs, channel errors, and SLA warnings are covered | RED: audit/security tests fail; UAT: failure and warning states |

## Evidence

- 018 provides sessions, events, interrupt/resume, and scoped variables required by handoff.
- 017 provides resource/tool/subworkflow evidence that observe can surface.
- 012/014 already introduced publish/open/observe shells that this spec makes runtime-backed.
