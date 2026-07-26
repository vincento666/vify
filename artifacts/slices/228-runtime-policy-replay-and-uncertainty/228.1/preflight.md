# 228.1 TDD Preflight

- Date: 2026-07-26
- Method: `tdd`
- Public interface: `RuntimePolicyReplayService` route-evaluation entrypoint
- First behavior: injected route runner result is compared with required case expectation
- RED predicate: deliberately wrong runner result cannot produce a passing report
- GREEN bound: deterministic local fixture only; provider usage remains zero
- Scope: evaluation contract/runner only; governance composition remains 228.2
- First implementation write / TTL start: 2026-07-26
