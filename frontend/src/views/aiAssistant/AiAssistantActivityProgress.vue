<template>
  <span class="ai-activity-progress" data-testid="ai-assistant-activity-progress">
    步骤 {{ progress.current }}/{{ progress.total }}
  </span>
</template>

<script setup lang="ts">
import type { RunActivityProgress } from './aiAssistantActivityView'

defineProps<{
  progress: RunActivityProgress
}>()
</script>

<style scoped>
.ai-activity-progress {
  display: inline-flex;
  align-items: center;
  margin-left: 0.375rem;
  padding: 0.125rem 0.375rem;
  color: var(--color-primary-600, #4f46e5);
  background: var(--color-primary-50, #eef2ff);
  border-radius: 999rem;
  font-size: 0.6875rem;
  line-height: 1.25;
}
</style>
