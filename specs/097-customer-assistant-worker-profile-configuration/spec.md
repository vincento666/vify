# Feature Spec: Customer Assistant Worker Profile Configuration

## Status

Slice 097.1 complete.

## User Story

As an operator/demo admin, I can change the customer-assistant worker profile for a task type during a demo so that the next recognized task uses the configured worker, prompt, model policy, tools, and risk policy without editing environment variables or restarting the service.

## Functional Requirements

- Expose a mutation API for `任务类型 -> worker/chatflow/workflow/react worker -> 模型/提示词/工具/风险策略` profile entries.
- Persist profile overrides in the database so they survive service rebuilds and test-client requests.
- Merge persisted overrides over the default/env catalog, keeping existing GET and task-recognition behavior compatible.
- Route new customer assistant task recognition through the persisted override immediately.
- Return configured profile refs in task-recognition/operator evidence exactly as existing catalog profiles do.
- Add a lightweight workbench edit flow so the configured worker profile is visible and editable from the operator surface.

## Non-Goals

- Full enterprise profile lifecycle, RBAC-specific admin screens, or multi-tenant approval workflows.
- Removing env/default catalog support.
- Changing task recognition intent behavior beyond profile resolution.

## Acceptance Criteria

- RED evidence shows the mutation API is initially missing.
- Backend integration verifies PATCH persists a profile, GET returns it, and the next customer turn routes to the configured worker refs.
- Frontend API and workbench tests verify profile update calls and visible edit flow.
- Browser UAT proves an operator can edit a task profile from the customer assistant workbench and see the updated profile evidence.
- Rem gate and focused frontend unit tests pass for UI changes.
- Docs/tasks record evidence paths and final status.

## Evidence

- RED backend: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/red-backend.txt`
- RED frontend: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/red-frontend.txt`
- Backend worker-profile integration: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/backend-worker-profiles.txt`
- Backend schema/migration gate: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/backend-schema.txt`
- Ruff: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/ruff.txt`
- Frontend focused/unit/rem/build: `frontend-focused.txt`, `frontend-unit-focused.txt`, `frontend-unit-full.txt`, `frontend-rem.txt`, `frontend-build.txt`
- Browser UAT: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/uat.txt`
- Browser UAT screenshot: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/worker-profile-edit.png`
