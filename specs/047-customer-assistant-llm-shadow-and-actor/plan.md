# Plan 047: Customer Assistant LLM Shadow And Actor

## Architecture

Extend the existing customer-assistant module in place:

```text
app/modules/customer_assistant/
├── domain/
│   ├── actor.py
│   ├── shadow.py
│   ├── service.py
│   └── models.py
├── infra/
│   ├── repository.py
│   └── schema.py
└── web/
    ├── router.py
    └── schemas.py
```

Expected frontend touch points:

```text
frontend/src/api/customerAssistant.ts
frontend/src/views/customerAssistant/customerAssistantRuntime.ts
frontend/src/views/customerAssistant/customerAssistantViewModel.ts
```

## Actor Persistence Plan

Add a small domain type for actor validation:

```text
CustomerAssistantActor = customer | operator | system
```

Thread actor through:

```text
CustomerAssistantTurnRequest
  -> CustomerAssistantService.handle_turn
  -> create_run input payload / actor column
  -> RuntimeEvent actor
  -> TaskCommand input_snapshot
  -> WorkerResult context snapshots where needed
  -> API event formatting
```

Do not use actor to choose a different controller or scheduler in 047.

## Shadow Runtime Plan

Add a shadow runner that can be called from the existing service without
changing the controlled ReAct core:

```text
deterministic task recognition
  -> record baseline commands
  -> optional task_recognition shadow
  -> continue deterministic runtime path

deterministic aggregation
  -> record baseline recommendation
  -> optional recommendation shadow
  -> return deterministic result
```

The shadow runner writes debug events through the existing repository event
append path.

## Shadow Client Plan

Provide two implementations:

```text
FakeCustomerAssistantShadowClient
ProviderBackedCustomerAssistantShadowClient
```

The provider-backed implementation resolves model configuration through
`ProviderModelFacade` and calls `ProviderBackedOpenAIChatClient`.

All shadow prompts must ask for strict JSON only. Parsing must validate the
schema before persisting `shadow` output.

## Diff Plan

Keep diff deterministic and simple in 047:

- task recognition: compare command type, task type, task key, worker type;
- recommendation: compare non-empty fields, warnings count, proposed customer
  draft presence;
- include raw baseline and parsed shadow output in debug payload;
- include a compact `matches` boolean and `differences` list for 051 export.

## Testing Strategy

Required tests:

- API contract test for `actor` defaulting and validation;
- repository/integration test for actor persistence in runs and events;
- frontend API client test proving `actor` is sent;
- unit test for fake task-recognition shadow event;
- unit test for fake recommendation shadow event;
- unit test proving shadow failure does not fail the turn;
- live LLM UAT test gated behind explicit env/config marker.

Required gates:

- focused backend customer-assistant tests;
- focused frontend customer-assistant tests;
- rem governance if frontend visual files are touched;
- browser UAT only if the visible panel changes.

## Evidence

Save evidence under:

```text
artifacts/slices/047-customer-assistant-llm-shadow-and-actor/
```

Use subdirectories matching task ids such as `047.1`, `047.2`, etc.
