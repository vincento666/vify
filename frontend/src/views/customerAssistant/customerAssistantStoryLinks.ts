import type { LocationQuery, LocationQueryRaw } from 'vue-router'

interface DemoStoryLike {
  storyId: string
}

export function customerAssistantStoryIdFromQuery(query: LocationQuery): string | null {
  const raw = query.story
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string') return null
  const storyId = value.trim()
  return storyId.length > 0 ? storyId : null
}

export function selectCustomerAssistantDemoStoryToOpen(
  stories: DemoStoryLike[],
  queryStoryId: string | null,
  selectedStoryId: string | null,
): string | null {
  if (stories.length === 0) return null
  const queryStory = queryStoryId ? stories.find((story) => story.storyId === queryStoryId) : null
  const storyId = queryStory?.storyId ?? stories[0].storyId
  return storyId === selectedStoryId ? null : storyId
}

export function buildCustomerAssistantStoryQuery(
  currentQuery: LocationQuery,
  storyId: string,
): LocationQueryRaw {
  return {
    ...currentQuery,
    story: storyId,
  }
}
