# Implementation Plan

1. Add RED frontend coverage for the operator knowledge Q&A API contract,
   runtime read-only submit path, view-model formatting, and workbench UI
   region.
2. Implement the minimal API client and typed Q&A state.
3. Add a runtime helper that posts the current session question and stores only
   the Q&A response.
4. Format sources, task evidence, warnings, and context summary into compact
   display rows.
5. Render a small operator panel with question input, answer, sources,
   evidence, warnings, and context summary.
6. Run focused customer-assistant frontend tests, the rem gate, and browser
   UAT; save all outputs in the 112.1 artifact directory.
7. Update tasks/spec evidence status and commit if all gates pass.
