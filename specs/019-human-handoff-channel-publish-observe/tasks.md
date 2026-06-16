# Tasks 019: Human Handoff, Channels, Publish, And Observe

## 019.1 TRANSFER_TO_HUMAN node and ticket model

- [x] RED: transfer-to-human node and handoff ticket tests fail.
- [x] Add handoff ticket model, schemas, repository, and service.
- [x] Add `TRANSFER_TO_HUMAN` node metadata, card, config panel, and executor.
- [x] Update Chatflow session status on handoff.
- [x] Add E2E: Chatflow transfers to human and handoff ticket is visible.
- [x] Save evidence under `artifacts/slices/019-human-handoff-channel-publish-observe/019.1/`.
- [x] Gates pass.

## 019.2 Channel adapter contract and Web/API channels

- [x] RED: channel adapter contract tests fail.
- [x] Implement API channel adapter.
- [x] Implement Web channel adapter or preview adapter.
- [x] Map channel identity into `sys.channel`, `sys.channel_id`, `sys.conversation_id`, and `sys.user_id`.
- [x] Show disabled third-party channel shells with clear unavailable reason.
- [x] Add E2E: published Chatflow runs through API/Web channel profile.
- [x] Save evidence under `artifacts/slices/019-human-handoff-channel-publish-observe/019.2/`.
- [x] Gates pass.

## 019.3 Versioned publish and rollback

- [x] RED: versioned publish tests fail.
- [x] Implement immutable published version snapshots.
- [x] Implement active version pointers and rollback.
- [x] Implement publish validation for graph, resources, channel config, handoff queue, and secrets.
- [x] Update publish modal and open/API shell to use active version.
- [x] Add E2E: publish, run active version, rollback.
- [x] Save evidence under `artifacts/slices/019-human-handoff-channel-publish-observe/019.3/`.
- [x] Gates pass.

## 019.4 Observe surfaces

- [x] RED: observe API and frontend tests fail.
- [x] Implement observe run/session/handoff/metrics APIs with filters and pagination.
- [x] Add run trace detail with node inputs, outputs, resource calls, events, and errors.
- [x] Add observe frontend route/tab.
- [x] Link debug dock run detail to observe detail.
- [x] Add E2E: run flow, open observe, inspect trace and metrics.
- [x] Save evidence under `artifacts/slices/019-human-handoff-channel-publish-observe/019.4/`.
- [x] Gates pass.

## 019.5 Ops/security polish

- [x] RED: audit, sanitization, channel error, and SLA warning tests fail.
- [x] Add audit records for publish, rollback, channel update, handoff assign/close, and return-to-bot.
- [x] Sanitize observe logs and handoff transcript snapshots.
- [x] Add channel delivery error states.
- [x] Add SLA warning states for handoff tickets.
- [x] Capture Browser UAT for publish failure, channel disabled, handoff queue, observe trace, and sanitized logs.
- [x] Save evidence under `artifacts/slices/019-human-handoff-channel-publish-observe/019.5/`.
- [x] Gates pass.
