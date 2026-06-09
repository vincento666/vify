## UAT

- No visual surface changed in this slice.
- Verified through frontend API/model unit tests that runtime-lab fallback Agent configuration is exposed and summarized.
- Verified production type-check/build accepts `updateRuntimeLabFallbackAgent` as returning a concrete `fallbackAgent`.

## Gates

- RED: `red.txt`
- Unit: `unit.txt`
- Build: `build.txt`
