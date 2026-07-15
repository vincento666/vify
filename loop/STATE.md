# Loop State

## Current

- date: 2026-07-13
- mode: Closed Loop
- active contract: Spec 225 Workflow/Chatflow Control Hardening
- current unit: 225.5 Live Intent binding, Runtime V2 parity, provider credential readiness, and closeout
- implementation: 225.1 through 225.4 deterministic gates complete; 225.5 Runtime V2/model-binding, provider/client readiness, and terminal-output projection repairs pass; the user-authorized 15-call live matrix is PASS
- branch: codex/workflow-chatflow-control-hardening
- base: 1ee8dc5e
- merge target: not selected
- worktree: isolated and clean at contract start
- oversight: human-on-the-loop

## Confirmed Evidence

- 225.0 passes a real-Chromium Workflow/Chatflow list regression: Delete is
  the sole row action, a row click enters the matching canvas, and confirmed
  Delete removes the row without navigating away.
- 225.1 passes a Workflow/Chatflow real-Chromium geometry matrix at 1536,
  1200, 896, 840, 740, and 620px, including panel/no-panel and clipped-scroll
  cases where applicable. Evidence:
  `artifacts/slices/225-workflow-chatflow-control-hardening/225.1-visible-stage-toolbar/`.
- At 896px the full right panel now shelves before it would leave only 131px
  of visible stage for a 303px toolbar.
- `CONDITION` and `VARIABLE_AGGREGATION` show drag handles that are neither
  draggable nor wired to a reorder handler; Intent rows are the working model.
- 225.2 now proves the Workflow and Chatflow reorder paths with real Chromium:
  condition branch and aggregation value drag, save, reload, direct API
  readback, and cleanup all pass. The automatic blank aggregation candidate
  intentionally has no draggable handle.
- 225.3 now proves all 20 node panels in both modes: standalone selectors use
  a full control rail, output format selectors fit their rail, and structured
  type selectors remain between 4rem and 9rem without escaping the panel.
  The former 42px knowledge-resource select and 51px information-collection
  scope select are covered by browser REDs and repaired.
- All `›` and `⌄` glyph chevrons in the shared canvas source were replaced by
  Lucide SVGs; Open, config sections, variable source flyouts, and publish
  sections pass real-Chromium icon checks for both modes.
- Existing unit tests confirm upstream-only graph catalog behavior and local
  inline template catalog behavior.
- 225.4 passes a cleanable Workflow/Chatflow lifecycle matrix: three condition
  routes, selected-node MESSAGE events, browser config save/reload, debug,
  publish, and selected-version invocation.
- 225.4 passes the cleanable variable-scope matrix in both modes; input
  references exclude sibling branches and message inline references are local.
- 48 focused runtime/contract tests pass across deterministic node execution,
  external-resource seams, interrupts/resumes, and capability parity.
- In-app Browser UAT passed one actual Workflow and one actual Chatflow run;
  their temporary fixtures were deleted afterward.
- Final Spec 225 unit/rem gates pass 76 tests; final focused E2E gates pass.
- `npm --prefix frontend run build` is blocked only by the pre-existing,
  out-of-scope `src/api/aiAssistant.test.ts:162` `modelMode` type mismatch;
  the failure is recorded in Spec 225 evidence and was not changed.
- The first configured Qwen provider was found to have no usable key; that
  false-positive `authConfigured` state is covered by the provider/client
  readiness repair. The user then cleared local providers and configured a
  fresh OpenRouter-compatible provider externally; local connection discovery
  succeeded and the single enabled `qwen/qwen3.5-9b` model is available. No
  credential is copied into source, artifacts, environment files, or loop
  state.
- Static Runtime V2 inspection finds `INTENT_RECOGNITION` calling
  `IntentRecognitionNodeExecutor()` without the runtime LLM completer, so
  `classifierMode=llm` falls back to fake classification on canonical async
  runs. This must be repaired and regression-tested before marking intent UAT
  as a real live-model path.
- Intent's current configuration panel exposes `fake` / `llm` but no model
  selector. The available node-config completer requires that model id when an
  explicit node-config provider is used, so the UI cannot reliably bind the
  user-selected Qwen model to an LLM intent node.
- 225.5 RED is reproduced by
  `test_chatflow_runs_v2_uses_node_model_config_for_llm_intent`: an LLM-mode
  Intent reaches a terminal route but no request reaches its configured fake
  provider client, proving Runtime V2 supplied no completer.
- 225.5 Runtime V2 GREEN now resolves a node-config completer for LLM-mode
  Intent nodes and sends it through the existing governed external-node path.
- 225.5 Intent model-binding RED/GREEN passes a real Chromium Workflow and
  Chatflow save/reload regression; LLM-mode Intent nodes expose and persist the
  shared Qwen model selection without issuing a model request.
- Browser UAT exposed frontend validation that required a literal `end` key;
  valid named END nodes in a multi-branch graph could not start a trial run.
  The repair recognizes END nodes by type and has focused Workflow validation
  and canvas-validation regression coverage.
- Publish gating expands the complete two-mode lifecycle to twelve calls; its
  conservative upper bound is USD 0.0025056 (24,576 prompt + 320 completion
  tokens), below the authorized USD 0.10 cap.
- The first Workflow live composite stopped at client-side authorization-header
  validation before a provider HTTP request/completion. It made no retry or
  further live call, and its temporary Workflow, Chatflow, and Agent fixtures
  were deleted. No provider billing receipt was generated; zero billable spend
  is an inference from the transport-free failure, not an external assertion.
- Provider responses now report blank/unresolved API-key configurations as not
  configured, and the OpenAI-compatible client fails missing credentials before
  opening transport. Focused provider/client regression tests pass.
- After discovering that the old `18080` service belonged to another worktree,
  the current worktree was verified on isolated backend `18081` and frontend
  `15175`. All seven no-model-call Workflow/Chatflow browser E2E gates pass
  there, including the three-route streaming/selected-node/publish lifecycle.
- The current live pricing preflight reports USD 0.10/M input and USD 0.15/M
  output. The user explicitly extended the 12-call matrix to 15 after a real
  Chatflow browser defect; the 15-call conservative upper bound is about USD
  0.003132, below the USD 0.10 cap.
- Live Browser UAT completed the Workflow and Chatflow draft and published
  Runtime V2 lifecycle (15 completions). Each chain traversed LLM-mode Intent,
  the two-condition route, LLM, Agent, and END without provider error or retry.
  Outputs and credentials are omitted from evidence.
- The successful Chatflow draft result initially reached the backend as an END
  `final` output while the browser showed no reply. RED proved terminal Runtime
  V2 event projection dropped `payload.output`; the focused frontend repair
  now projects it. A new real Chatflow browser run visibly displayed the reply,
  and its published Runtime V2 invocation independently completed successfully.

## Next Action

Live UAT and focused regression gates now pass. Perform the normal final diff
review/commit gate when the user requests a commit; no more live calls are
authorized or needed.

## Waiting Human

None for the live gate. Credentials remain outside this worktree. A separate
independent reviewer/commit decision is still required by the repository loop
before merge delivery.
