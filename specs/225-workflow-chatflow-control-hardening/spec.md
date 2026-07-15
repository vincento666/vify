# Spec 225: Workflow/Chatflow Control Hardening

## Goal

Repair reproducible Workflow and Chatflow authoring/list regressions without
changing their public API or runtime payload contracts. Authors must be able to
enter a canvas directly from a minimal list, configure dense node panels,
reorder every visually draggable row, keep the bottom toolbar in the visible
canvas stage, and understand variable/reference boundaries from the UI.

## Scope

- Shared Workflow/Chatflow canvas chrome and node configuration UI.
- Workflow/Chatflow list entry: row opens its canvas; delete is the sole row
  action; the legacy Workflow detail drawer is removed.
- All palette node types: START, END, LLM, KNOWLEDGE, API_CALL, TOOL_CALL,
  EXECUTE_WORKFLOW, AGENT_CALL, TRANSFER_TO_HUMAN, CODE, CONDITION,
  INTENT_RECOGNITION, TEXT_PROCESS, JSON_PARSE, VARIABLE_AGGREGATION,
  VARIABLE_ASSIGN, MESSAGE, QUESTION, HUMAN_INPUT, and INFORMATION_COLLECTION.
- Configuration persistence, selected-node test affordance, variable-picker
  scope, deterministic Workflow/Chatflow lifecycle UAT, and opt-in live-model
  UAT for LLM-backed paths.
- **225.5 only:** the canonical Runtime V2 execution path for
  `INTENT_RECOGNITION` in `classifierMode=llm`, plus the shared Intent panel
  model binding required to configure that path honestly.
- **225.5 live-gate incident only:** provider credential-readiness reporting and
  preflight, limited to preventing an empty API key from being presented as a
  runnable model or sent as an invalid authorization header.

## Non-goals

- No backend/API/schema/runtime semantic change, new dependency, or redesign of
  the canvas information architecture, except the narrowly scoped 225.5
  Runtime V2 completer wiring that prevents an explicitly configured LLM intent
  from silently taking the fake-classifier path and the credential-readiness
  preflight needed to keep the authorized live gate honest.
- No weakened validation, mock substitution for the requested live-model gate,
  or persistent test fixtures left behind.
- No broader Workflow/Chatflow list redesign beyond the stated minimal entry
  behavior.

## Design Contract

The shared authoring surface uses a restrained **field rail**: labels and
controls have stable visual measure, structured rows preserve a clear primary
value column, icon-only affordances use existing Lucide components, and the
toolbar centers in the visible canvas stage rather than the hidden page area.
The current indigo/green semantic palette remains unchanged; this is a density
and interaction repair, not a visual reskin.

## Slices

0. **225.0 Minimal list entry**: retain only Delete as the row action, remove
   the Workflow detail drawer, and route a row click to its corresponding
   canvas without allowing Delete to navigate.
1. **225.1 Visible-stage toolbar**: reproduce and repair toolbar clipping or
   left-rail overlap at all responsive phases, including a selected node panel
   and node-test drawer.
2. **225.2 Honest structured-row drag**: make condition-branch and
   variable-aggregation handles reorder and persist; audit Intent drag against
   inert/foreign drops and preserve its persisted ordering behavior.
3. **225.3 Config control rail**: normalize standalone/resource selectors and
   structured row widths, replace remaining arrow glyphs with icons, and make
   node cards/config sections legible at the supported panel widths.
4. **225.4 Complete authoring/lifecycle audit**: run the all-node configuration
   matrix, verify upstream versus local variable reference limits, test
   streaming and selected-node-test availability, and execute Workflow and
   Chatflow save/debug/publish/call paths. Run live LLM-backed cases only after
   the user confirms provider/model and a spend cap.
5. **225.5 Live Intent binding and Runtime V2 parity**: expose the existing
   model selector when an Intent node uses `classifierMode=llm`; bind the
   selected model to its persisted config; and execute that intent through the
   governed Runtime V2 LLM completer rather than the fake fallback.

## Acceptance

- Workflow and Chatflow list rows expose only Delete; clicking a non-action
  area enters the matching canvas, and confirming Delete stays in the list and
  removes the row.
- At 1536, 896, 840, 740, and 620 CSS-pixel widths, the bottom toolbar is
  fully visible, centered in the visible stage, and does not overlap the left
  resource rail or a panel overlay.
- Every displayed drag handle has a working reorder action and persisted order;
  no non-draggable handle remains for Condition or Variable Aggregation.
- Standalone selectors consume their field rail; structured selectors neither
  collapse below their defined readable minimum nor overflow their panel.
- The canvas has no literal chevron/arrow UI glyph where an existing Lucide
  icon expresses the affordance.
- Input/reference popovers expose only reachable upstream outputs plus enabled
  configured scopes; inline message/template popovers expose only node-local
  declared input variables (END uses local output variables).
- The all-node configuration matrix persists values and retains hidden
  capabilities such as streaming, selected-node testing, and variable popovers.
- Canvas validation recognizes every `type: END` node, not only a node with the
  legacy `end` key, so valid multi-branch graphs can be trial-run and published.
- Deterministic Workflow and Chatflow lifecycle UAT passes. The authorized
  live LLM matrix also passes with redacted artifacts: real LLM-mode Intent,
  Condition, LLM, Agent, and END execution in draft and published Runtime V2
  paths for both modes, without provider retry or error.
- An Intent node set to `classifierMode=llm` exposes the shared model selector,
  persists its selection in Workflow and Chatflow, and canonical async Runtime
  V2 invokes the configured completer under its normal external-node guard.
- A provider with a blank direct key or unresolved environment key is not
  advertised as `authConfigured`; an attempted provider completion fails before
  opening HTTP with an explicit missing-credential error.
- The authorized live matrix uses only the configured `qwen/qwen3.5-9b` model,
  has at most 15 planned model calls and USD 0.10 total spend, uses compact
  redacted prompts, limits Intent to 16 output tokens and LLM/Agent calls to 32,
  first verifies a conservative pricing bound, stops on the first provider
  error, and never retries a case automatically.

## Evidence

`artifacts/slices/225-workflow-chatflow-control-hardening/{slice}/`

## Current evidence status

- 225.0: PASS with a real-Chromium row-entry/delete regression in both modes.
- 225.1–225.3: PASS with focused unit/rem, real-Chromium E2E, and Browser UAT.
- 225.4 deterministic authoring/lifecycle audit: PASS.
- 225.4 live-model portion: PASS under 225.5 with the configured
  `qwen/qwen3.5-9b` model. The original empty-credential preflight was
  repaired; after explicit expansion from 12 to 15 compact calls, both modes
  pass draft and published Runtime V2 lifecycle evidence with all fixtures
  deleted.
- 225.5 Runtime V2 Intent binding and Intent model-selector persistence: PASS.
- 225.5 credential-readiness repair: PASS with focused provider/client tests.
