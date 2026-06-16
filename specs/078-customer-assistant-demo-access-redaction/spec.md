# 078 Customer Assistant Demo Access Redaction

## Goal

Protect the productized customer-assistant demo surface with host-provided
operator, tenant, and permission context, while keeping demo-friendly local
development behavior intact.

## Acceptance Criteria

- Customer-assistant product endpoints reuse the existing host request context
  headers (`X-Hify-Actor-Id`, `X-Hify-Tenant-Id`, `X-Hify-Permissions`,
  `X-Hify-Source`, `X-Request-Id`).
- Embedded/non-local hosts must provide explicit permissions:
  `customer_assistant:read` for read-only views and
  `customer_assistant:operate` for session turns, action mutation, task control,
  worker refresh/cancel, and other operator actions.
- Local source remains backwards-compatible for existing contract tests and
  developer demos.
- Session context records sanitized host metadata for auditability without
  exposing request tokens, API keys, customer phones, order numbers, or raw tool
  payloads.
- Backend contract and integration tests prove missing permissions fail with a
  403 envelope and allowed operators can run the existing demo loop.

## Slices

### 078.1 Backend Demo Access Boundary

Add customer-assistant host context, permission checks, and sanitized session
metadata at the router/service boundary. Include browser-side fetch UAT for
denied read, denied operate, allowed turn, and metrics read.

### 078.2 Response Redaction And Ref Ownership

Redact task/event/action/worker/sub-agent response payloads and enforce
tenant/operator ownership for secondary references such as `runId`, `actionId`,
and `workerRunId`.

### 078.3 Workbench Host Context UAT

Run the customer-assistant workbench through a host runtime config that supplies
operator and tenant permissions, then prove the visible demo still works.

## Evidence

Evidence lives under
`artifacts/slices/078-customer-assistant-demo-access-redaction/<slice>/`.

## Non-goals

- Full production authentication, SSO, JWT validation, or tenant-scoped database
  partitioning.
- Cross-module RBAC unification beyond the customer-assistant MVP demo boundary.

## Known Follow-ups

- Native EventSource cannot inject custom headers, so the current SSE path still
  needs a follow-up auth strategy before strict embedded-host enforcement.
- Full response redaction and object ownership are tracked in 078.2.
