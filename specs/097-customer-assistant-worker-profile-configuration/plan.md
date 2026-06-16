# Implementation Plan: Customer Assistant Worker Profile Configuration

## Slice 097.1 Runtime-Editable Worker Profiles

1. Add RED backend integration test for profile PATCH persistence and routing.
2. Add DB table and repository methods for profile overrides.
3. Extend worker profile catalog merge semantics so DB overrides trump env/default profiles.
4. Add service/router/schema mutation endpoint guarded by operate permission.
5. Add frontend API client test and implementation.
6. Add a compact workbench edit flow for worker profile refs.
7. Run backend integration/schema gates, frontend focused tests, rem gate, and browser UAT.
8. Commit the feature as a focused MVP capability point.

## Evidence Directory

`artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/`
