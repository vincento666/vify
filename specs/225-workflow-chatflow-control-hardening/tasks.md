# Tasks 225: Workflow/Chatflow Control Hardening

## 225.0 Minimal list entry

- [x] RED: current lists expose `查看`, `画布`, and `删除` rather than Delete-only.
- [x] Remove the Workflow detail drawer and duplicate actions; make rows enter their matching canvas.
- [x] Real-Chromium UAT proves both modes keep Delete in-list and delete the row after confirmation.

## 225.1 Visible-stage toolbar

- [x] RED: browser geometry test proves 620px left-rail + node panel clips or overlaps the toolbar.
- [x] Implement only the shared toolbar/stage positioning repair.
- [x] Unit/rem/E2E/Browser UAT evidence: Workflow and Chatflow at all responsive phases.

## 225.2 Honest structured-row drag

- [x] RED: Condition and Aggregation visual handles do not reorder/persist while Intent does.
- [x] Implement reorder semantics and usable handles for Condition branches and Aggregation variables; guard Condition/Intent against no-source drops.
- [x] Unit/E2E/browser evidence includes save/reload persistence and fixture cleanup.

## 225.3 Config control rail and iconization

- [x] RED: all-node geometry audit finds collapsed/overwide selectors or literal arrow glyphs.
- [x] Implement shared sizing/grid breakpoints and replace remaining chevron glyphs with Lucide icons.
- [x] Unit/rem/E2E/browser evidence covers resource, output, structured and standalone controls.

## 225.4 All-node lifecycle and live gate

- [x] RED: audit fixtures retain the 225.3 product REDs; the 225.4 full-run stream probe was corrected to the supported selected-node/Runtime V2 event contract. Fixtures clean themselves on success/failure.
- [x] Run all-node configuration persistence, streaming, selected-node-test and variable-scope matrix.
- [x] Run deterministic Workflow/Chatflow save, debug, publish and invoke lifecycle UAT.
- [x] Run redacted live LLM UAT under the authorized 225.5 USD 0.10 cap;
  user-authorized 15-call extension covers the repaired Chatflow visual reply
  confirmation and its published-version invocation.

## 225.5 Live Intent binding and Runtime V2 parity

- [x] RED: canonical Runtime V2 invokes an LLM-mode Intent with no completer,
  so it silently uses the fake classifier.
- [x] GREEN: use the existing governed external-node route and configured
  completer only for `classifierMode=llm`; preserve fake-mode behavior.
- [x] RED: an Intent configured as `llm` has no model selector in either canvas
  mode.
- [x] GREEN: show and persist the shared selector for LLM-mode Intent nodes in
  Workflow and Chatflow.
- [x] RED: a valid multi-branch graph using named END node keys fails canvas
  validation with `END node is required`.
- [x] GREEN: validate END nodes by node type and accept reachability to any END
  key.
- [x] RED: a provider with `authConfig: {api_key: ''}` is listed as
  `authConfigured`, allowing a non-runnable live model to be selected.
- [x] GREEN: report only a usable direct/environment key as configured and
  fail a missing-key completion before transport.
- [x] Run the first compact Browser lifecycle composite under the cap; stop on
  the empty-credential provider error without retry, redact evidence, and
  delete all temporary fixtures.
- [x] Resume compact real Browser lifecycle composites for Intent + Condition +
  LLM + Agent after external provider configuration; Workflow and Chatflow
  draft/published Runtime V2 calls pass and fixtures are cleaned.

## Final Gate

- [x] `git diff --check`, focused unit/rem suites, and applicable E2E all pass.
- [x] Full frontend build is run; unchanged out-of-scope failures are recorded, never hidden.
- [x] Browser UAT artifacts and exact PASS/BLOCKED status are recorded under the Spec 225 path.
- [x] `spec.md`, `plan.md`, `tasks.md`, and loop state reflect actual results only.
