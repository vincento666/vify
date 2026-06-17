# Plan

## Slice 154.1

1. Add integration RED coverage for invalid worker profile PATCH requests.
2. Preserve empty configured refs through mapping so validation can distinguish omitted values from explicitly blank values.
3. Add service-layer validation for supported worker types, blank policy refs, blank tool refs, and duplicate tool refs.
4. Run MySQL8 integration/contract gates and ruff.

## Gates

- RED evidence: `artifacts/slices/154-customer-assistant-worker-profile-validation-gate/154.1/red.txt`
- Integration evidence: `artifacts/slices/154-customer-assistant-worker-profile-validation-gate/154.1/integration.txt`
- Contract evidence: `artifacts/slices/154-customer-assistant-worker-profile-validation-gate/154.1/contract.txt`
- Ruff evidence: `artifacts/slices/154-customer-assistant-worker-profile-validation-gate/154.1/ruff.txt`
- UAT note: `artifacts/slices/154-customer-assistant-worker-profile-validation-gate/154.1/uat.md`
