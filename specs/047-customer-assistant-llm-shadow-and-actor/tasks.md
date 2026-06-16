# Tasks 047: Customer Assistant LLM Shadow And Actor

## 047.0 Spec Sign-off

- [x] Confirm 047 follows completed 045 and 046.
- [x] Confirm 047 introduces `actor`, not channel/source.
- [x] Confirm `source` remains component source for runtime events and worker
      evidence.
- [x] Confirm shadow mode never controls ledger mutation, worker dispatch,
      proposed actions, or final response.
- [x] Confirm live LLM shadow is opt-in gate only.
- [x] Save sign-off evidence under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.0/`.

## 047.1 Actor API And Persistence

- [x] RED: backend contract test fails for missing `actor` support on
      `/customer-assistant/sessions/{sessionId}/turns`.
- [x] Add `actor` to turn request schema with default `customer`.
- [x] Validate actor values: `customer`, `operator`, `system`.
- [x] Include actor in idempotency request hash.
- [x] Persist actor in run input payload and runtime events.
- [x] Include actor in formatted event API output.
- [x] Ensure omitted actor remains backwards-compatible.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.1/`.

## 047.2 Actor Frontend Contract

- [x] RED: frontend API client test proves payload currently drops actor.
- [x] Replace local `source?: 'customer' | 'operator'` turn payload with
      `actor?: 'customer' | 'operator' | 'system'`.
- [x] Send actor through `sendCustomerAssistantTurn`.
- [x] Keep customer lane default actor as `customer`.
- [x] Keep operator lane actor as `operator` if operator input remains enabled.
- [x] Do not implement operator-specific runtime branching.
- [x] Run focused frontend tests and rem gate if touched files require it.
- [x] Save evidence under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.2/`.

## 047.3 Shadow Configuration And Fake Client

- [x] RED: unit test fails because shadow settings/client do not exist.
- [x] Add customer-assistant shadow settings with safe defaults:
      `mode=off`, task recognition enabled, recommendation enabled.
- [x] Add shadow domain schemas for task-recognition output and recommendation
      output.
- [x] Add fake shadow client that returns deterministic strict JSON.
- [x] Add shadow parser that rejects invalid JSON/schema without throwing into
      the main runtime path.
- [x] Add event helpers for `llm_shadow_started`, `llm_shadow_completed`,
      `llm_shadow_failed`, and `llm_shadow_diff_recorded`.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.3/`.

## 047.4 Task-Recognition Shadow

- [x] RED: runtime test fails because fake task-recognition shadow is not
      emitted.
- [x] Invoke task-recognition shadow after deterministic commands are produced.
- [x] Persist baseline commands, parsed shadow commands, actor, latency, and
      compact diff as debug events.
- [x] Prove shadow commands do not mutate the ledger or change worker dispatch.
- [x] Prove shadow parse/client failure records a debug event and the main turn
      still succeeds.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.4/`.

## 047.5 Recommendation Shadow

- [x] RED: runtime test fails because fake recommendation shadow is not
      emitted.
- [x] Invoke recommendation shadow after deterministic aggregation.
- [x] Persist baseline recommendation, parsed shadow recommendation, actor,
      latency, and compact diff as debug events.
- [x] Prove shadow recommendation does not change `operatorRecommendation` or
      `customerReplyDraft`.
- [x] Prove shadow failure records a debug event and the main turn still
      succeeds.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.5/`.

## 047.6 Live LLM Shadow UAT

- [x] Add provider-backed shadow client using `ProviderModelFacade`,
      `OpenAIChatRequestBuilder`, `ProviderBackedOpenAIChatClient`, and
      `OpenAIAdapterParser`.
- [x] Add explicit live UAT marker/env guard so default tests do not call the
      network.
- [x] Run fake-mode regression gate.
- [x] When credentials/model config are available, run one live task-recognition
      shadow and one live recommendation shadow. N/A in this run:
      `HIFY_CUSTOMER_ASSISTANT_LIVE_SHADOW_UAT` was unset, so live network UAT
      was explicitly skipped instead of falsely greened.
- [x] Save live UAT notes and event payload samples under
      `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.6/`.

## 047.7 Final Acceptance

- [x] Run focused customer-assistant backend tests.
- [x] Run focused customer-assistant frontend tests.
- [x] Run existing 045/046 regression gates or document unrelated failures.
- [x] Confirm shadow mode off produces no LLM calls.
- [x] Confirm fake shadow mode records structured events.
- [x] Confirm actor persistence is visible through event list API.
- [x] Update docs with final evidence links.

## Evidence

- 047.0 sign-off:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.0/signoff.md`
- 047.1 backend RED/green:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.1/red.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.1/unit.txt`
- 047.2 frontend RED/green:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.2/red.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.2/unit.txt`
- 047.3 shadow unit RED/green:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.3/red.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.3/unit.txt`
- 047.4 task shadow RED/green:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.4/red.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.4/unit.txt`
- 047.5 recommendation shadow RED/green:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.5/red.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.5/unit.txt`
- 047.6 live opt-in notes:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.6/uat.md`
- 047.7 final gates and UAT:
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.7/backend.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.7/frontend.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.7/e2e.txt`,
  `artifacts/slices/047-customer-assistant-llm-shadow-and-actor/047.7/uat.md`
