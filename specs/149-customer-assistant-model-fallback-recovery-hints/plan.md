# Plan: 149.1 Model Fallback Recovery Hints

## Slice

Add a presentation-only recovery layer on top of existing model fallback
evidence.

1. Add RED view-model assertions for `recoveryHints`.
2. Add RED panel contract assertions for the recovery hint block.
3. Implement hint derivation in `customerAssistantViewModel.ts`.
4. Render the hint block in `CustomerAssistantPanel.vue`.
5. Add a browser UAT fixture with `llm_primary_fallback`, a failed task, and a
   visible retry control.
6. Reuse the eval redaction boundary for timeline payload previews and metrics
   failure summaries so fallback evidence cannot leak customer phone numbers.

## Verification

- Focused customer-assistant view-model/panel tests.
- `remScaleClosure`.
- Full frontend unit and build.
- Browser UAT with screenshot.

## Result

Completed. Final evidence is saved under
`artifacts/slices/149-customer-assistant-model-fallback-recovery-hints/149.1/`.
