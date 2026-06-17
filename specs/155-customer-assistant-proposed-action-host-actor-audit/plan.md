# Plan

## Slice 155.1

1. Add RED integration coverage for host actor propagation through confirm, execute, and reject.
2. Resolve customer-assistant operator actor from `RequestContext`, falling back to `operator` for local/default contexts.
3. Use the resolved actor in proposed-action confirm/reject/execute/deliver lifecycle events and task-command confirmation side effects.
4. Run targeted integration, contract, and ruff gates.

## Gates

- RED evidence: `artifacts/slices/155-customer-assistant-proposed-action-host-actor-audit/155.1/red.txt`
- Integration evidence: `artifacts/slices/155-customer-assistant-proposed-action-host-actor-audit/155.1/integration.txt`
- Contract evidence: `artifacts/slices/155-customer-assistant-proposed-action-host-actor-audit/155.1/contract.txt`
- Ruff evidence: `artifacts/slices/155-customer-assistant-proposed-action-host-actor-audit/155.1/ruff.txt`
- UAT note: `artifacts/slices/155-customer-assistant-proposed-action-host-actor-audit/155.1/uat.md`
