<template>
  <section class="ai-activity-feed" data-testid="ai-assistant-activity-feed">
    <AiAssistantSubagentPresence
      :activities="activities"
      :expansion-overrides="expansionOverrides"
      :now-ms="nowMs"
      @toggle="$emit('toggle', $event)"
    />
    <slot :now-ms="nowMs" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { RunActivity } from './aiAssistantActivity'
import type { ActivityExpansionOverrides } from './aiAssistantActivityView'
import AiAssistantSubagentPresence from './AiAssistantSubagentPresence.vue'

const props = defineProps<{
  activities: RunActivity[]
  expansionOverrides: ActivityExpansionOverrides
}>()

defineEmits<{
  toggle: [activity: RunActivity]
}>()

const nowMs = ref(Date.now())
let timer: number | null = null
const hasLiveActivity = computed(() => props.activities.some((activity) => (
  activity.status === 'running'
  || activity.status === 'queued'
  || activity.status === 'waiting_approval'
)))

function startClock() {
  if (timer !== null || !hasLiveActivity.value) return
  timer = window.setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
}

function stopClock() {
  if (timer !== null) window.clearInterval(timer)
  timer = null
}

watch(hasLiveActivity, (active) => {
  if (active) startClock()
  else stopClock()
})

onMounted(startClock)
onBeforeUnmount(stopClock)
</script>

<style scoped>
.ai-activity-feed {
  display: grid;
  gap: 0;
  min-width: 0;
  padding: 0.25rem 0.25rem 0.375rem;
  background: var(--color-bg-surface, #ffffff);
}
</style>
