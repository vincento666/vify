# Customer Assistant Runtime

## Chatflow SOP worker invocation

Spec 213.4 makes bound `chatflow_sop` workers async-first by default.

Production bootstrap uses `customer_assistant_sop_runtime_invocation_mode = "async"` unless explicitly overridden. When a worker starts a bound Chatflow SOP, the first customer-assistant turn returns:

- task `lastResult.status = WAITING`
- `workerAsyncRefs` for the customer-assistant worker run
- Chatflow runtime v2 refs under `lastResult.evidence.runtimeRefs`
- top-level `chatflowSession` refs (`runId`, `statusRef`, `eventsRef`, `eventStreamRef`, `nodesRef`, `resultRef`)
- a queued `RuntimeJob` for the Chatflow runtime run

The sync path is still available only as an explicit fallback for tests or local debugging:

```text
HIFY_CUSTOMER_ASSISTANT_SOP_RUNTIME_INVOCATION_MODE=sync
```

With sync fallback enabled, the same worker waits for the Chatflow runtime result inline and does not enqueue a background runtime job.

Follow-up turns reuse the `runId` captured in the worker checkpoint. If the child Chatflow runtime is still starting, the bridge first advances that durable run to a waiting or terminal state, then resumes it with the new customer input. If the run is still not ready, the worker returns the same async refs as `WAITING` instead of falling back to a v1/failed checkpoint.

The Chatflow SOP LLM node mode is controlled separately from customer-assistant task recognition and recommendation LLMs:

```text
HIFY_CUSTOMER_ASSISTANT_SOP_LLM_MODE=live  # default; provider-backed when a live agent/model is configured
HIFY_CUSTOMER_ASSISTANT_SOP_LLM_MODE=mock  # deterministic runtime v2 mock for ordinary UAT / non-live gates
```

Ordinary non-live UAT should use `mock` so gateway, refs, recovery, and worker ledger behavior do not depend on external provider availability. Live provider validation remains explicit through live gates.
