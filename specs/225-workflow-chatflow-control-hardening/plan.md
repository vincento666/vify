# Plan 225: Workflow/Chatflow Control Hardening

## Boundaries

- Implement only in the existing Workflow/Chatflow list and shared canvas
  frontend surfaces, focused frontend tests/E2E scripts, the narrowly scoped
  Runtime V2 Intent completer wiring, and the provider/client credential
  preflight revealed by the authorized live run.
- Preserve graph serialization, `/api/v1` contracts, and existing node type
  taxonomy. The 225.5 runtime change must reuse the existing governed external
  node path and must not alter fake Intent behavior.
- Use existing Lucide imports/components; do not add a styling or drag library.

## Design System

- **Subject / user / job:** a workflow author configures one node precisely
  while retaining orientation in a dense canvas.
- **Signature:** field rails: full-width standalone controls, measured label /
  value rows, fluid `minmax(0, …)` structured grids, and visible-stage canvas
  chrome.
- **Responsive rule:** toolbar geometry derives from the visible stage/rail,
  never from off-screen canvas width. Structured rows stack before their type
  selector becomes unreadable.
- **Accessibility:** icon buttons retain labels/titles; draggable controls use
  focusable, named handles or explicit accessible ordering controls if native
  drag alone cannot expose a usable path.

## Verification Matrix

| Area | Deterministic evidence | Browser evidence |
|---|---|---|
| Responsive chrome | geometry regression test | Workflow + Chatflow at five widths and panel states |
| Minimal list entry | row-action/delete contract | Workflow + Chatflow list-to-canvas/delete flow |
| Drag order | persisted graph/order test | Condition, Aggregation, Intent comparison |
| All nodes | configuration persistence matrix | each palette node panel and hidden controls |
| Variable rules | `variableCatalog` unit coverage | upstream picker and local inline picker |
| Lifecycle | API/graph validation | save, debug, publish, invoke for both flow types |
| Live LLM | explicit provider capability record | LLM-mode Intent, LLM, and Agent real-case composites |
| Intent Runtime V2 | completer-injection regression | persisted Intent model binding in both modes |

## External Gate

The user authorized the discovered OpenRouter-compatible `qwen/qwen3.5-9b`
model for this contract with a **USD 0.10** total cap. The original matrix had
12 planned model calls: a successful draft canvas run and a published-version
invocation for both Workflow and Chatflow; each composite has Intent, LLM, and
Agent calls. A real Chatflow browser regression then required rerunning its
draft after a frontend repair, and the user explicitly authorized expansion to
15 calls. Intent output is capped at 16 tokens; LLM/Agent outputs at 32 tokens.
Before requests, read model pricing and reject the run unless a conservative
upper bound is below the cap. Redact prompts and outputs, stop at the first
provider error, make no automatic retry, and delete temporary test data after
evidence capture.

## Current Status

225.5 Runtime V2 Intent binding and model selection pass under TDD. The initial
empty-credential block led to a provider/client readiness repair. After secure
external provider setup, the user authorized 15 compact calls: Workflow and
Chatflow draft/publish/published Runtime V2 paths pass with real LLM-mode
Intent, Condition, LLM, Agent, and END execution. A live Chatflow reply
projection defect was found and repaired under TDD; its browser confirmation
and published invocation now pass. All temporary fixtures were deleted.
