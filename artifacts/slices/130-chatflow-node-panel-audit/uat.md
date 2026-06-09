## UAT

- Audited chatflow node panel E2E coverage for Start, End, LLM, Message/Question/Human Input, Information Collection, Intent Recognition, Transfer to Human, Execute Workflow, Resource Context, LLM selector/prompt hardening, shared variable picker, and running path animation.
- Updated shared variable picker acceptance to match the current product contract: END answer content references upstream/system variables such as `sys.query` and inserts `{{start.sys.query}}`; it no longer expects a local-only `output` variable.
- Confirmed the picker still shows compact labels without raw `{{...}}` in the option list and persists the inserted reference after saving/reloading.

## Gates

- RED: `red-chatflow-shared-variable-picker.txt`
- E2E: `e2e-*.txt`
- Unit: `unit.txt`
- Build: `build.txt`
