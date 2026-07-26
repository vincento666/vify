# 228.1 Reviewer Round 2

- Verdict: REQUEST CHANGES
- Prior HIGH findings: closed.
- MEDIUM: `known_gap` cases did not enforce full `RouteEvalCase` schema and a malformed
  gap could coexist with a passing required report.

Directed repair round: 2 / 3.

Fix:

- required and known-gap cases now share one structural validation contract;
- any case validation error adds `route_evaluation.case_contract_invalid`;
- malformed known gaps cannot be counted as pass or ride through a passing report.
