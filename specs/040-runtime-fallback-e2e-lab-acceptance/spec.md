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

## Specification Sign-off

Status: ready for implementation.

Numbering was rechecked on 2026-06-09. 040 is the final acceptance spec for
033 and 036-039, with 035 as the knowledge retrieval dependency. It must not
introduce new product scope beyond closing evidence gaps for the runtime
fallback stack.
