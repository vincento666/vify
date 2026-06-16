# Spec 088: Customer Assistant Demo Story Deeplink

## Goal

Make the productized customer-assistant demo easier to present by opening a
seeded story automatically and preserving the selected story in the URL.

## Acceptance Criteria

- When seeded stories are available and no story is selected yet, the workbench
  auto-opens the first story.
- When the URL contains `?story=<storyId>` and that story exists, the workbench
  opens that story.
- When the operator switches stories, the URL query is updated to the selected
  story id without losing unrelated query parameters.
- Invalid or empty story query values do not crash the panel and fall back to the
  first available seeded story.

## Non-goals

- Do not change backend demo seed behavior.
- Do not change visual layout or CSS in this slice.
- Do not add new demo stories.

## Evidence

Evidence lives under
`artifacts/slices/088-customer-assistant-demo-story-deeplink/088.1/`.
