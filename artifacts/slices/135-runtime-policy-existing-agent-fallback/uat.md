# 135 Runtime Policy Existing Agent Fallback

## Scope

- Build a runtime-lab fallback Agent from a `fallbackAgent.type = existing_agent` RuntimePolicyProfile snapshot when a SQLAlchemy session and valid `agentId` are available.
- Route the fallback through the existing ChatService stack, including knowledge, workflow, MCP, and provider facades.
- Keep invalid/missing `agentId` or missing session as `None`, preserving safe opt-in behavior.

## Evidence

- `unit.txt`: `tests/unit/runtime_policy/test_runtime_factories.py` passed.

## Result

PASS. Existing-agent fallback construction and execution contract is green.
