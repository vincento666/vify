# Spec 040: Runtime Fallback E2E And Lab Acceptance

## Goal

Prove the complete runtime routing stack end to end, including handoff, FAQ,
semantic FAQ, SOP, RAG, controlled Agent fallback, clarification, and browser
lab observability.

040 is the acceptance spec after 033 and 036-039. It does not introduce new
route policy primitives unless a gap is found during acceptance.

## Dependency

Required:

- 033 complete;
- 036 complete;
- 037 complete;
- 038 complete;
- 039 complete;
- 034 lab page available for browser UAT;
- 035 knowledge retrieval productization available.

## Scope

In scope:

- backend E2E scenarios for every route layer;
- runtime-lab API evidence consistency;
- frontend lab inspector support for fallback route evidence if existing UI is
  insufficient;
- browser UAT for realistic airline service conversations.

Out of scope:

- new fallback algorithms;
- production human-agent console;
- live LLM mandatory CI.

## Required E2E Scenario Matrix

1. explicit handoff: user asks for human support during no-active context;
2. explicit handoff during active SOP preserves task state/context;
3. exact FAQ answers before SOP arbitration;
4. active SOP FAQ answer does not consume a slot;
5. semantic FAQ paraphrase answers with embedding/rerank evidence;
6. long-tail document question returns RAG answer with citations;
7. ambiguous active SOP input asks clarification;
8. repeated clarification failure escalates to handoff;
9. unresolved long-tail query reaches controlled Agent fallback;
10. Agent handoff recommendation routes through policy;
11. normal SOP start/switch/resume/complete still passes;
12. non-interruptible SOP switch rejection still passes.

## Acceptance Criteria

- all scenarios pass through `/api/v1/runtime-lab/sessions/{id}/messages`;
- route evidence identifies source layer and final action;
- FAQ/RAG/Agent outputs never enter SOP intent classifier candidates;
- active/suspended task state is preserved for answer-only fallback paths;
- browser UAT shows route action, route source, evidence, task ledger, and final
  reply for representative scenarios;
- full backend and frontend gates pass or unrelated failures are documented.

## Completion Capability

After 040, the system is a complete controlled customer-service routing runtime:

- strict SOP handling for civil-aviation business flows;
- multi-intent switch/resume with task ledger;
- early handoff hard stops;
- FAQ exact and semantic answers;
- RAG answers with citations;
- controlled Agent fallback;
- clarification and escalation;
- browser-visible evidence for manual business acceptance.

## Completion Evidence

Status: completed on 2026-06-09.

Evidence:

- RED: `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.1/red.txt`
- E2E matrix: `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.1/e2e.txt`
- Targeted backend gate: `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.1/final-targeted.txt`
- Low RAG -> Agent hardening:
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.2/red-low-rag-agent.txt`
- Fake Agent handoff hardening:
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.2/red-fake-agent-handoff.txt`
- Browser UAT:
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.3/browser-uat-result.json`
- Browser screenshot:
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.3/screenshots/runtime-040-browser-docs.png`
- Full backend scan:
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.3/full-backend.txt`

Final targeted result: `50 passed, 1 warning`.

Full backend scan result: `477 passed, 8 skipped, 13 failed, 1 warning`. The
remaining failures are documented baseline failures outside the 033/036-040
targeted runtime fallback stack.

## Specification Sign-off

Status: completed.

Numbering was rechecked on 2026-06-09. 040 is the final acceptance spec for
033 and 036-039, with 035 as the knowledge retrieval dependency. It must not
introduce new product scope beyond closing evidence gaps for the runtime
fallback stack.
