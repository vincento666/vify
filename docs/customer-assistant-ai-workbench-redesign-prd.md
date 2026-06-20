# Customer Assistant AI Workbench Redesign PRD

Status: Slice 1 implemented
Date: 2026-06-20
Owner: Product / Runtime Architecture

## Goal

Refactor the customer assistant right-side workbench around operator tasks and
business objects instead of runtime internals. The first shipped slice keeps the
existing customer-assistant runtime and API gateway, but changes the operator
surface so the default view highlights only the information needed to serve the
traveler.

Design principles:

- User task first: the operator sees intent, emotion, next handling step,
  recommended script, and pending business confirmations before runtime detail.
- Business object first: tasks, proposed actions, customer reply drafts, and
  audit evidence are grouped by what the operator needs to do.
- Progressive disclosure: technical worker/profile/event evidence is available,
  but not in the default view.

## Implemented Information Architecture

The page remains a one-screen three-column shell:

- Left column: multi-customer session and story navigation.
- Center column: traveler/customer conversation and operator passenger-facing
  reply composer.
- Right column: AI workbench with five tabs.

### Right Tab 1: 聚焦

Default tab. It contains only operator-critical cards:

- `意图识别` / `情绪识别`
- `业务办理指引` / `话术推荐`
- `SOP办理进度`
- `业务办理确认` / `高敏确认`

The recommendation card exposes icon actions:

- send recommendation to traveler;
- copy recommendation;
- send recommendation to the operator editor;
- regenerate guidance through the assistant path.

The confirmation card uses the same `workspace.proposedActions` state as the
full business panel and AI assistant tab, so confirm/reject status is shared.
The default tab intentionally hides worker, model, prompt, raw runtime event,
and profile configuration terms.

### Right Tab 2: AI助手

This tab is the operator's AI assistant chat window. It is one conversational
surface rather than a stack of business or runtime panels:

- header: assistant availability and current context;
- message stream: user follow-up questions and assistant replies;
- composer: operator follow-up Q&A or knowledge questions.

This tab is where the operator asks follow-up questions or knowledge questions.
The center column remains the simulated passenger conversation and does not
contain assistant tooling. Business progress, confirmation cards, metrics,
worker controls, and audit/event evidence do not appear in this tab; they stay
in `聚焦`, `办理`, `证据`, or `配置` according to their operator purpose.

### Right Tab 3: 办理

This tab contains full business handling:

- task ledger;
- task controls;
- recommendation detail;
- proposed action editor and receipts;
- customer reply draft;
- risk warnings.

Worker/model/prompt details remain out of this tab unless they are needed as
business-facing evidence elsewhere.

### Right Tab 4: 证据

This tab contains deeper evidence and audit material:

- evaluation observability;
- recognition evidence;
- operator advisory evidence;
- operator audit log.

The tab is intended for troubleshooting and confidence checks after the operator
has the main business answer.

### Right Tab 5: 配置

This tab contains worker profile configuration. It is separated because these
settings are not normal operator work and should eventually move to an admin or
workspace configuration surface.

## Runtime And Bridge Contract

Slice 1 keeps the existing customer-assistant runtime, proposed-action API, and
AI assistant bridge contracts. The UI relies on the existing durable state:

- `workspace.proposedActions` drives confirmation cards in `聚焦` and `办理`;
- `operatorKnowledgeQa` drives the AI assistant Q&A result;
- runtime and worker events remain available in evidence/event panels;
- worker profile configuration remains reachable in `配置`.

The backend task-control confirmation path now flushes deferred async worker
submissions and task listing consumes completed worker results. This preserves
the expected bridge behavior where a confirmed retry can recover a failed task
and the UI/API readback sees the completed worker result.

## Acceptance Gates

Evidence is saved under:

`artifacts/slices/customer-assistant-ai-workbench-redesign/`

Completed gates:

- RED: focused UI contract and Q&A fallback tests failed before implementation.
- Frontend unit: customer-assistant focused tests and full frontend unit suite.
- Frontend rem: `src/remScaleClosure.test.ts`.
- Frontend build: `npm --prefix frontend run build`.
- Backend unit: customer-assistant unit tests plus AI assistant tool registry.
- Backend integration: customer-assistant integration suite.
- Backend contract: customer-assistant contracts plus AI assistant bridge API.
- Browser UAT: final mocked business flow and real-stack layout smoke.
- In-app browser smoke: visible 5228 page shows `聚焦 / AI助手 / 办理 / 证据 / 配置`
  with the default focus pane visible.

## Remaining Follow-Ups

Later slices can deepen the product without expanding this slice's scope:

- productize a dedicated customer-assistant Copilot context/harness policy;
- move worker profile configuration out to an admin surface;
- add richer execution-tree projection for task attempts;
- add source-cited knowledge retrieval as a stronger backend contract;
- seed real local demo data for the in-app browser path when the local database
  is empty.
