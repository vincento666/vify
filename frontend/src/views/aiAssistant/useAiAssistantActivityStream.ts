import { ref } from 'vue'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import { projectRunActivities, type RunActivity } from './aiAssistantActivity'
import {
  activityTimelineItems,
  buildRunActivityFeed,
  isActivityExpanded as resolveActivityExpanded,
  withActivityExpansion,
  type ActivityExpansionOverrides,
} from './aiAssistantActivityView'
import { buildAiAssistantTimeline } from './aiAssistantTimeline'

export function useAiAssistantActivityStream() {
  const activityExpansionOverrides = ref<ActivityExpansionOverrides>({})

  function activitiesForEvents(events: AiAssistantEvent[]) {
    return projectRunActivities(events)
  }

  function feedItemsForEvents(events: AiAssistantEvent[]) {
    return buildRunActivityFeed(events)
  }

  function timelineItemsForActivity(activity: RunActivity, events: AiAssistantEvent[]) {
    return activityTimelineItems(activity, buildAiAssistantTimeline(events))
  }

  function isActivityExpanded(activity: RunActivity) {
    return resolveActivityExpanded(activity, activityExpansionOverrides.value)
  }

  function toggleActivity(activity: RunActivity) {
    activityExpansionOverrides.value = withActivityExpansion(
      activityExpansionOverrides.value,
      activity,
      !isActivityExpanded(activity),
    )
  }

  function resetActivityExpansionOverrides() {
    activityExpansionOverrides.value = {}
  }

  return {
    activityExpansionOverrides,
    activitiesForEvents,
    feedItemsForEvents,
    timelineItemsForActivity,
    isActivityExpanded,
    toggleActivity,
    resetActivityExpansionOverrides,
  }
}
