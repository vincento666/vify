## Slice Notes

- Scope: align node/panel audit E2E contracts with current workflow/chatflow product rules.
- Condition nodes are selector-only, so the all-node variable audit asserts they do not expose a generic `输入` section.
- Schema mapping variable pickers must keep the new minimal picker and expose simple expandable-row arrows instead of old icon-heavy sources.
- Start and End nodes must not expose selected-node test actions; the six-node matrix now asserts that while continuing to run middle-node standalone tests.
- Browser UAT is covered by the Playwright E2E audits for this test-contract slice; no product UI code changed.
