# Plan

## Slice 153.1

1. Add an E2E red test to the Runtime Lab Chatflow SOP v2 path.
2. Assert the trace exposes raw Runtime v2 refs.
3. Fetch `eventsRef` and assert durable raw events retain SOP caller context across wait and resume.
4. Implement the smallest Runtime Lab trace formatter change.
5. Run E2E and relevant integration tests against MySQL8.

## Gates

- RED evidence: `artifacts/slices/153-runtime-lab-sop-v2-raw-event-debug-trace/153.1/red.txt`
- E2E evidence: `artifacts/slices/153-runtime-lab-sop-v2-raw-event-debug-trace/153.1/e2e.txt`
- Integration evidence: `artifacts/slices/153-runtime-lab-sop-v2-raw-event-debug-trace/153.1/integration.txt`
- Ruff evidence: `artifacts/slices/153-runtime-lab-sop-v2-raw-event-debug-trace/153.1/ruff.txt`
- UAT note: `artifacts/slices/153-runtime-lab-sop-v2-raw-event-debug-trace/153.1/uat.md`
