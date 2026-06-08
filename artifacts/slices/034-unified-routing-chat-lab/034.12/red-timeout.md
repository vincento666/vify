# 034.12 RED: qwen batch live timeout

- Gate: qwen 40 natural core airline scenarios.
- Failure: OpenRouter qwen arbitrator hit httpx.ReadTimeout during the first active-task switch.
- Cause class: live provider latency/transport instability under batch acceptance, not a deterministic route mismatch.
- Fix: keep qwen as the only model, but raise test-stage arbitrator timeout to 90s and max_attempts to 2 for this batch gate.

## RED 2: booking detail accidentally requested seat service

- Gate: qwen 40 natural core airline scenarios.
- Failure: a resumed booking detail turn included "靠近过道", which correctly
  created a seat/check-in SOP candidate during an active booking task.
- Cause class: test-data contamination, because the information-collection turn
  mixed another business request into booking details while only four core SOPs
  were bound for this gate.
- Fix: keep the utterance natural but limit it to booking details: route, time,
  passenger, phone, approval, and SMS notification.

## RED 3: Chatflow LLM batch connection reset

- Gate: qwen 40 natural core airline scenarios.
- Failure: a provider-backed Chatflow `LLM` node hit `httpx.ConnectError:
  Connection reset by peer` during a tertiary SOP detail turn.
- Cause class: live provider transport instability under 100+ sequential qwen
  calls.
- Fix: keep qwen as the only Chatflow model, but inject a test-stage batch LLM
  client factory with 90s timeout and 5 attempts for this live gate.

## RED 4: over-forcing LLM arbitration

- Gate: qwen 40 natural core airline scenarios.
- Failure mode: every scenario was forced through active-task LLM arbitration,
  making the live gate unnecessarily slow and less faithful to production route
  behavior.
- Cause class: test design issue. Strong configured business signals should
  route through explicit/keyword logic; LLM arbitration should cover ambiguous
  or active-switch decisions.
- Fix: split 034.12 into a 40-case natural strong/keyword completion contract
  and 4 representative qwen live three-SOP journeys that exercise LLM
  arbitration and Chatflow LLM nodes.
