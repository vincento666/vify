# 229.2 Builder preflight

- `loop/context-pack.sh --role builder`: loaded 2026-08-01.
- `loop/hooks/skill-preflight.sh --required tdd`: `AVAILABLE tdd`.
- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`.
- Base: `815cb1c90031a9dfb1e11e325a1ecf6ed48c0441`.
- Starting delivered head: `11052f51991fa4b420459ffead6ce4668502dcac`.
- Local MySQL8: healthy through the repository compose service; no Weaviate or
  live/paid provider call.

Unrelated Loop harness drift was present before 229.2 and is excluded from the
slice manifest and staging set.
