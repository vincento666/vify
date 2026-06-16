# Plan 094

## 094.1 Recognition Evidence Surface

- Capture RED backend coverage proving `task_recognized` lacks profile
  references.
- Persist profile references into `task_recognized.payload.commands[]`.
- Add a frontend view-model formatter for recognition evidence rows.
- Render the operator recognition evidence panel.
- Extend browser UAT to verify backend event evidence and frontend visibility.

## Gates

- RED backend test before implementation.
- Green focused customer-assistant backend integration tests.
- Green focused customer-assistant frontend view-model and panel tests.
- Green frontend rem gate.
- Green full frontend unit suite and build.
- Green browser UAT with screenshot evidence.
