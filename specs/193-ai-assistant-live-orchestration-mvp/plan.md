# Plan 193: AI Assistant Live Orchestration MVP

## Slice 193.1 Live Model And Event Transport

1. Add RED contract tests for per-run `modelConfig`, streamed deltas, and SSE
   event transport.
2. Extend the OpenAI-compatible chat client with streaming completion support.
3. Let `QwenLivePlanner` forward provider deltas to the harness as they arrive.
4. Add an async message-start endpoint and event-stream endpoint.
5. Keep synchronous `/messages` behavior for existing contracts by reusing the
   same start/complete path.

## Slice 193.2 Product Shell Realtime UX

1. Add RED frontend tests for model config controls, async start API, event
   stream helper, and no frontend tool heuristic.
2. Add temporary model configuration controls with Chinese copy.
3. Submit live runs through the async endpoint and subscribe to SSE events.
4. Refresh inspector/task state as terminal, approval, tool, and stream events
   arrive.
5. Tighten no-inline-border styling contract.

## Slice 193.3 Evidence And UAT

1. Run focused backend contract/unit/e2e gates.
2. Run frontend unit and `remScaleClosure`.
3. Run real-browser UAT for a complex read/write/skill-intent journey.
4. Record residual risks, especially provider/network flakiness and local skill
   execution being intentionally deferred.
