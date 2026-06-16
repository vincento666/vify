# Plan 058: Realtime Runtime Transport And Workflow/Chatflow V2 Spike

## Spike Candidate

Prefer Chatflow first because customer assistant already calls Chatflow/SOP as a
bounded worker capability.

Prefer the database path aligned with the MySQL 8 migration. If the migration is
not ready, the spike must explicitly mark itself as a persistence prototype and
must not be treated as production-ready.

Candidate API:

```text
POST /api/v1/chatflows/{chatflowId}/runs-v2
GET /api/v1/runtime-runs/{runId}
GET /api/v1/runtime-runs/{runId}/events/stream
GET /api/v1/runtime-runs/{runId}/result
```

## Compatibility

Existing endpoints remain:

```text
POST /api/v1/chatflows/{chatflowId}/runs
POST /api/v1/workflows/{workflowId}/runs
```

They may internally call v2 later, but must preserve response shape.

## Data Readiness

Before implementation, verify:

- target database contains the Chatflow definition used by the spike;
- migration/seed path can recreate the definition;
- runtime event rows can be read after process restart;
- missing definition errors are surfaced as data-readiness failures.

## Event Envelope

Use the 053 envelope:

```text
id
runId
sequence
type
level
source
actor
nodeId
spanId
parentSpanId
payload
createdAt
```

## UAT

Run Browser UAT on both:

- customer assistant operator panel;
- workflow/chatflow debug surface used by the spike.
