# Plan 051: Customer Assistant Eval Data Foundation

## Architecture

Add a lightweight eval package:

```text
app/modules/customer_assistant_eval/
├── schemas.py
├── exporter.py
├── runner.py
└── fixtures/
```

If a separate module is too heavy during implementation, keep it under
`app/modules/customer_assistant/eval/` but preserve the same boundaries.

## Export Path

```text
customer_assistant_event
  -> normalize candidate case
  -> redact unsafe/private fields
  -> write JSONL fixture/report artifact
```

## Test Strategy

- exporter unit tests;
- golden case runner tests;
- report snapshot tests;
- no live model dependency.
