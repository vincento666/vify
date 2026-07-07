# Browser UAT - 214.5

Status: PASS

Environment:

- Frontend: `http://127.0.0.1:15177`
- Backend: `http://127.0.0.1:18085`
- Local fake OpenAI provider for shared-DB runtime-lab SOP scale only: created in `uat-local-fake-provider.txt`, cleaned in `uat-local-fake-provider-cleanup.txt`

RED evidence:

- Runtime-lab SOP scale initially failed at `group_booking` waiting for `COMPLETE_TASK`: `red-sop-scale.txt`
- Runtime result contract initially omitted terminal `sessionId`: `red-runtime-result-session-id.txt`

Passed UAT groups:

- Chatflow seven-script gate: `uat-chatflow.txt`
- Workflow seven-script gate: `uat-workflow.txt`
- Runtime-lab SOP v2 binding and unified-routing scale gate: `uat-sop.txt`

Result:

- Chatflow scripts passed after backend restart.
- Workflow scripts passed after backend restart.
- Runtime-lab scale passed 15 airline SOP scenarios and 5 switch scenarios.
- Shared MySQL UAT fixture rows were disabled/deleted after the run.
