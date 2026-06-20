# Customer Assistant AI Workbench Redesign PRD

Status: Spec 207 Slice A RED contract captured; implementation pending
Date: 2026-06-20
Owner: Product / Runtime Architecture

## Goal

Refactor the customer assistant right-side workbench around a single default
operator handling surface. The previous split between `聚焦` and `办理` created
two places for one closure loop. The new target removes `办理` and moves normal
business handling into `聚焦`.

## Principles

- One default handling surface: the operator closes the current traveler task
  from `聚焦`.
- Chat stays chat: `AI助手` is a pure assistant conversation, not a second task
  dashboard.
- Research/debugging stays visible but secondary: `证据` and `配置` remain
  reachable and are clearly marked as `研究调试入口`.
- Passenger conversation stays in the center lane; internal task controls stay
  out of the customer lane.

## Target Information Architecture

The page remains a one-screen three-column shell:

- Left column: multi-customer session and story navigation.
- Center column: traveler/customer conversation and operator passenger-facing
  reply composer.
- Right column: AI workbench with four tabs only.

### Right Tab 1: 聚焦

Default tab. It contains the complete operator handling loop:

- status bar;
- task intent and emotion;
- business object summary;
- SOP handling tree;
- risk and SLA/time-limit status;
- recommended reply card;
- sensitive confirmation card;
- task ledger;
- recommendation detail;
- customer reply draft;
- risk warnings;
- confirmation controls;
- execution, delivery, and decision receipts;
- task controls such as retry/cancel/resume where supported.

The `聚焦` pane may share existing durable state such as
`workspace.proposedActions`, but it must not expose worker/profile/configuration
internals as default operator work.

### Right Tab 2: AI助手

This tab is a pure chat window:

- assistant message stream;
- operator follow-up composer;
- assistant answer messages.

It must not contain an internal tab header, task ledger, recommendation panel,
draft panel, risk panel, task controls, configuration panel, metrics panel, or
evidence dashboard. Business closure remains in `聚焦`.

### Right Tab 3: 证据

This tab is a research/debugging entry point. It contains deeper evidence and
audit material for troubleshooting and confidence checks:

- evaluation observability;
- recognition evidence;
- advisory evidence;
- audit log.

It must be labeled with `研究调试入口` so operators understand it is secondary to
normal handling.

### Right Tab 4: 配置

This tab is a research/debugging entry point for worker/profile configuration.
It remains reachable during the migration but is not part of normal task
handling. It must be labeled with `研究调试入口`.

## Removed IA

The right workbench must no longer include:

- `办理` tab;
- `business` active tab state;
- `operator-workbench-business-pane`;
- separate business-only panels outside `聚焦`.

## Slice A Contract

Slice A writes only SDD/PRD docs and the focused frontend contract test. The
contract is expected to fail against the current Vue implementation until a
later implementation slice updates the UI.

RED evidence:

`artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`

## Acceptance Gates

Slice A:

- SDD/PRD updated to the four-tab IA.
- Focused frontend contract requires the new target.
- Focused frontend unit test fails RED for the expected missing implementation.

Later implementation slices:

- Focused frontend contract green.
- Frontend rem gate green for any visual-size changes.
- Full frontend unit suite green.
- Browser UAT verifies right workbench tabs, default focus contents, and pure
  assistant chat behavior.
