# Tasks 189: AI Assistant Customer Assistant Subagent Bridge

## 189.0 Documentation Sign-Off

- [x] Create `189-ai-assistant-customer-assistant-subagent-bridge`.
- [x] Limit scope to PRD Phase 6 bridge tracer.
- [x] Declare read-only bridge behavior with no customer-assistant runtime
      writes.
- [x] Declare MySQL8-only persistence evidence.
- [x] Declare frontend/browser/rem gates not applicable unless frontend changes.

## 189.1 Backend Bridge Tracer

- [x] RED: unit and contract tests fail because
      `customer_assistant_subagent_bridge` does not exist.
- [x] Add read-only bridge tool manifest.
- [x] Add deterministic bridge handler using existing customer-assistant
      harness adapter ref helpers.
- [x] Prove AI Assistant API can call the tool and persist output.
- [x] Prove existing customer-assistant harness sub-agent contract remains
      green.
- [x] Run unit, contract, regression, ruff, mypy, and boundary scan gates.
- [x] Save evidence under
      `artifacts/slices/189-ai-assistant-customer-assistant-subagent-bridge/189.1/`.

## Later Slices

- [ ] Add a real spawn-and-track bridge if product requirements need AI
      Assistant to initiate customer-assistant runs.
- [ ] Add frontend presentation only if the product shell must surface these
      bridge refs directly.
- [ ] Add observability/benchmark governance in the Phase 7 spec.

