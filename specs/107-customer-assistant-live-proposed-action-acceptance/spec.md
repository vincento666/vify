# Feature Spec: Customer Assistant Live Proposed Action Acceptance

## Status

Complete for deterministic local-provider acceptance. Real-provider validation
is pending operator-provided credentials.

## User Story

As a demo operator preparing the productized customer assistant MVP, I need an
opt-in live acceptance gate that proves live-model customer assistant paths can
recognize tasks, generate recommendations, drive ReAct tool calls, and preserve
the proposed-action safety boundary for high-risk writes.

## Functional Requirements

- The existing `customer-assistant-live-react-acceptance` gate must remain
  CI-safe by default and skip without live credentials.
- When enabled with an OpenAI-compatible provider, the gate must require explicit
  category coverage for:
  - task recognition;
  - recommendation generation;
  - ReAct worker tool calls and event echo;
  - proposed-action safety boundaries.
- The proposed-action safety boundary category must validate that a live-model
  high-risk write tool call produces a pending proposed action instead of
  executing the tool.
- Gate artifacts must record category verdicts, live attempts, and boundary
  evidence without persisting provider secrets.
- Local deterministic acceptance coverage may use an OpenAI-compatible test
  server; real-provider execution remains opt-in through environment variables.

## Non-Goals

- Changing customer assistant demo seed data.
- Changing customer assistant UI files.
- Executing live providers in CI by default.
- Replacing the existing 072 live gate name or provider bridge.

## Acceptance Criteria

- RED test proves the enabled live gate used to pass without a dedicated
  `proposed_action_safety_boundaries` category.
- Unit tests prove missing required categories fail closed and artifact evidence
  is redacted.
- Acceptance tests prove the local OpenAI-compatible provider exercises all four
  categories.
- Default live acceptance remains skipped unless explicitly enabled.
- Real-provider command is documented for operators with credentials.
- Local deterministic evidence is complete; full live-provider evidence is not
  claimed until credentials are provided and the opt-in command is run.

## Evidence

Evidence lives under
`artifacts/slices/107-customer-assistant-live-proposed-action-acceptance/107.1/`.

- RED: `red.txt`
- Unit: `unit.txt`
- Acceptance local provider: `acceptance-local.txt`
- Acceptance default skip: `acceptance-skip.txt`
- Ruff: `ruff.txt`
