# Browser UAT

Backend-only runtime-v2 slice. No frontend route or user-visible browser flow was
changed, so Browser UAT is not applicable.

Runtime behavior was verified through FastAPI integration tests that exercise
the public runtime-v2 HTTP routes for start, events, nodes, result, resume, and
cancel.

