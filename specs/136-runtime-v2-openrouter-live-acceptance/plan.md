# 136 Plan

## Slice 136.1 Runtime V2 OpenRouter Live Gate

1. Record RED evidence for the missing acceptance file.
2. Add opt-in acceptance coverage for runtime v2 live LLM execution.
3. Enforce disposable database usage when the live gate is enabled.
4. Run default skip path.
5. Run ruff.
6. Run live OpenRouter DeepSeek V4 Flash acceptance.
7. Scan for accidental secret persistence.
8. Commit the slice.

## Evidence

- RED: `artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/red.txt`
- Default skip: `artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/default-skip.txt`
- Ruff: `artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/ruff.txt`
- Live runtime v2 gate: `artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/runtime-v2-openrouter-live.txt`
- Live markdown evidence: `artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/runtime-v2-openrouter-live.md`
