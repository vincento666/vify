# 221.10 Browser UAT

Status: GREEN

Environment:

- Frontend: `http://127.0.0.1:15187`
- Backend: `http://127.0.0.1:8000`
- Backend setting: `HIFY_RUNTIME_V2_REQUEST_THREAD_COMPLETION_ENABLED=false`
- Worker: `scripts/runtime_job_worker.py --owner both --worker-id runtime-v2-22110-worker --poll-interval 0.2`

Scripts:

- PASS `frontend/e2e/chatflow-conversation-run.mjs`
- PASS `frontend/e2e/chatflow-message-question-input.mjs`
- PASS `frontend/e2e/chatflow-information-collection.mjs`
- PASS `frontend/e2e/chatflow-intent-recognition.mjs`
- PASS `frontend/e2e/chatflow-transfer-to-human-node.mjs`
- PASS `frontend/e2e/chatflow-resume-api.mjs`
- PASS `frontend/e2e/chatflow-channels.mjs`
- PASS `frontend/e2e/workflow-chatflow-llm-run.mjs`
- PASS `frontend/e2e/api-resource-tool-builder.mjs`
- PASS `frontend/e2e/workflow-tool-call-node.mjs`
- PASS `frontend/e2e/workflow-transform-nodes.mjs`
- PASS `frontend/e2e/workflow-knowledge-condition-run.mjs`
- PASS `frontend/e2e/workflow-execute-workflow-node.mjs`
- PASS `frontend/e2e/workflow-agent-call-node.mjs`
- PASS `frontend/e2e/unified-routing-chat-lab-scale.mjs`

Note: `unified-routing-chat-lab-scale.mjs` requires `HIFY_E2E_BASE_URL=http://127.0.0.1:15187/runtime-lab/chat`; the first plain-base attempt failed route entry, then the corrected route passed.
