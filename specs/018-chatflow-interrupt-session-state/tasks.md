# Tasks 018: Chatflow Interrupt And Session State

## 018.1 Session, event, and checkpoint model

- [x] RED: session/event/checkpoint repository tests fail.
- [x] Add persistence models and schemas.
- [x] Add checkpoint store interface and database implementation.
- [x] Emit `message`, `interrupt`, `done`, and `error` events in fake runtime tests.
- [x] Save evidence under `artifacts/slices/018-chatflow-interrupt-session-state/018.1/`.
- [x] Gates pass.

## 018.2 Resume API

- [x] RED: resume API tests fail for QUESTION, HUMAN_INPUT, and INFORMATION_COLLECTION.
- [x] Implement resume request/response schemas.
- [x] Resume from checkpoint instead of START.
- [x] Merge resume data into execution context.
- [x] Add E2E: Chatflow asks a question, accepts reply, and completes same run.
- [x] Save evidence under `artifacts/slices/018-chatflow-interrupt-session-state/018.2/`.
- [x] Gates pass.

## 018.3 Scoped variables and bounded history

- [x] RED: variable scope resolution tests fail.
- [x] Implement external/system/conversation/user/channel/global/upstream resolver order.
- [x] Persist conversation variables with expiration metadata.
- [x] Persist user/channel variables according to current supported storage.
- [x] Add bounded history reader for LLM-driven nodes.
- [x] Add E2E: VARIABLE_ASSIGN writes conversation variable, later node reads it after resume.
- [x] Save evidence under `artifacts/slices/018-chatflow-interrupt-session-state/018.3/`.
- [x] Gates pass.

## 018.4 Runtime event timeline UI

- [x] RED: frontend event timeline tests fail.
- [x] Add Chatflow waiting-state panel and generated resume form.
- [x] Add event timeline to bottom debug dock.
- [x] Show checkpoint, current node, scoped variables, and resume output.
- [x] Capture Browser UAT screenshots for start, waiting, resume, done, and failure.
- [x] Save evidence under `artifacts/slices/018-chatflow-interrupt-session-state/018.4/`.
- [x] Gates pass.

## 018.5 Reliability guards

- [x] RED: idempotency, expiration, wrong-event, and duplicate-resume tests fail.
- [x] Implement idempotency key handling.
- [x] Reject expired sessions/checkpoints.
- [x] Reject resume for wrong run/event/session.
- [x] Render actionable errors in UI.
- [x] Save evidence under `artifacts/slices/018-chatflow-interrupt-session-state/018.5/`.
- [x] Gates pass.
