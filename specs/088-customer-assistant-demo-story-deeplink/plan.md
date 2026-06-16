# Plan 088

## 088.1 Story URL Selection

- Add RED unit coverage for story query parsing, initial auto-open selection,
  and route query preservation.
- Add a small helper for customer-assistant demo story link behavior.
- Wire the customer-assistant panel to Vue Router so seeded stories auto-open
  and selected story ids stay in `?story=...`.
- Add a focused browser UAT script that opens a seeded story by query and then
  switches stories.

## Gates

- RED helper unit failure before implementation.
- Green focused frontend unit tests.
- Frontend rem gate because a Vue file changes, even though this slice does not
  change CSS.
- Focused browser UAT.
