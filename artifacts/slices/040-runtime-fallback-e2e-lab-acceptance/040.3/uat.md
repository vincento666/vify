# 040 Browser UAT

Date: 2026-06-09

Target: `http://127.0.0.1:18088/api/v1/runtime-lab`

Runtime env:

- `HIFY_DATABASE_URL=sqlite:////tmp/hify_runtime_040_uat.db`
- `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=`
- `HIFY_RUNTIME_LAB_FAQ_KNOWLEDGE_BASE_IDS=1`
- `HIFY_RUNTIME_LAB_RAG_KNOWLEDGE_BASE_IDS=1`

Seed:

- FAQ exact: `儿童票可以退吗？`
- FAQ semantic embedding: `小朋友的票能不能退回来`
- RAG chunk: `航班延误超过4小时保险怎么赔？`

Result:

- 12/12 UAT cases passed. See `browser-uat-result.json`.
- Browser opened the live FastAPI docs page and captured `screenshots/runtime-040-browser-docs.png`.
- The browser security policy blocked `data:` and `file:` report pages, so the full table transcript is saved as JSON/HTML artifacts instead of a rendered report screenshot.

Cases:

1. no-active explicit handoff: PASS
2. active explicit handoff preserves active task: PASS
3. FAQ exact answers before classifier: PASS
4. active SOP FAQ does not consume slot: PASS
5. semantic FAQ evidence with rerank: PASS
6. RAG long-tail answer with citation: PASS
7. active ambiguous input clarifies by agent policy: PASS
8. repeated clarification escalates to handoff: PASS
9. unresolved query reaches controlled Agent fallback: PASS
10. Agent handoff recommendation is policy-gated: PASS
11. SOP start/switch/complete/resume: PASS
12. non-interruptible switch rejected: PASS

Full backend gate:

- `477 passed, 8 skipped, 13 failed, 1 warning`
- Failures are documented in `full-backend.txt`.
- Residual failures are existing non-040 baseline issues in runtime-lab scale/live suites and workflow knowledge stub signature tests.
