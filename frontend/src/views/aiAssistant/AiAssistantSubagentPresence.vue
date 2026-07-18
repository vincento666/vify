<template>
  <section
    v-if="presence.items.length"
    class="ai-subagent-presence"
    data-testid="ai-assistant-subagent-presence"
    aria-label="子智能体运行状态"
  >
    <header class="ai-subagent-presence__header">
      <TeamOutlined />
      <strong>子智能体</strong>
      <span v-if="presence.runningCount">{{ presence.runningCount }} 正在运行</span>
      <span v-else-if="presence.activeCount">{{ presence.activeCount }} 活跃</span>
      <span v-else>{{ presence.completedCount }} 已完成</span>
    </header>
    <article
      v-for="activity in presence.items"
      :key="activity.id"
      class="ai-subagent-presence__item"
      :class="`status-${activity.status}`"
      data-testid="ai-assistant-subagent-row"
    >
      <button
        type="button"
        :aria-expanded="isActivityExpanded(activity, expansionOverrides)"
        @click="$emit('toggle', activity)"
      >
        <LoadingOutlined v-if="activity.status === 'running'" class="ai-subagent-presence__spinner" />
        <CheckCircleOutlined v-else-if="activity.status === 'completed'" />
        <ExclamationCircleOutlined v-else-if="activity.status === 'failed'" />
        <ClockCircleOutlined v-else />
        <strong>{{ activity.title }}</strong>
        <small>{{ activity.summary }}</small>
        <span>{{ statusLabel(activity.status) }} · {{ activityElapsedLabel(activity, nowMs) }}</span>
        <RightOutlined
          class="ai-subagent-presence__chevron"
          aria-hidden="true"
          :class="{ expanded: isActivityExpanded(activity, expansionOverrides) }"
        />
      </button>
      <dl
        v-if="isActivityExpanded(activity, expansionOverrides)"
        class="ai-subagent-presence__details"
      >
        <div>
          <dt>执行标识</dt>
          <dd>{{ activity.executionId }}</dd>
        </div>
        <div v-if="activity.statusRef">
          <dt>状态引用</dt>
          <dd>{{ activity.statusRef }}</dd>
        </div>
        <div v-if="activity.resultRef">
          <dt>结果引用</dt>
          <dd>{{ activity.resultRef }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>

<script setup lang="ts">
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  RightOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'
import { computed } from 'vue'

import type { RunActivity } from './aiAssistantActivity'
import {
  activityElapsedLabel,
  isActivityExpanded,
  summarizeSubagentPresence,
  type ActivityExpansionOverrides,
} from './aiAssistantActivityView'

const props = defineProps<{
  activities: RunActivity[]
  expansionOverrides: ActivityExpansionOverrides
  nowMs: number
}>()

defineEmits<{
  toggle: [activity: RunActivity]
}>()

const presence = computed(() => summarizeSubagentPresence(props.activities))

function statusLabel(status: RunActivity['status']) {
  return {
    queued: '等待执行',
    running: '执行中',
    waiting_approval: '等待审批',
    completed: '已完成',
    failed: '执行失败',
    cancelled: '已取消',
  }[status]
}
</script>

<style scoped>
.ai-subagent-presence {
  display: grid;
  gap: 0.375rem;
  margin: 0.25rem 0.5rem 0.625rem 1.75rem;
  padding: 0.625rem;
  background: var(--color-primary-50, #eef2ff);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-subagent-presence__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-subagent-presence__header span {
  margin-left: auto;
  color: var(--color-primary-600, #4f46e5);
  font-size: 0.75rem;
}

.ai-subagent-presence__item button {
  width: 100%;
  display: grid;
  grid-template-columns: 1rem auto minmax(0, 1fr) auto auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.375rem;
  color: inherit;
  text-align: left;
  background: var(--color-bg-surface, #ffffff);
  border: 0;
  border-radius: var(--radius-sm, 0.25rem);
  cursor: pointer;
}

.ai-subagent-presence__item button:focus-visible {
  outline: 0.125rem solid var(--color-border-focus, #6366f1);
  outline-offset: 0.125rem;
}

.ai-subagent-presence__item strong,
.ai-subagent-presence__item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-subagent-presence__item small,
.ai-subagent-presence__item button > span {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
}

.ai-subagent-presence__chevron {
  width: 0.75rem;
  height: 0.75rem;
  color: var(--color-text-tertiary, #8b92a8);
  transition: transform 0.16s ease;
}

.ai-subagent-presence__chevron.expanded {
  transform: rotate(90deg);
}

.ai-subagent-presence__details {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0.5rem 0.375rem 0.25rem 1.5rem;
  color: var(--color-text-secondary, #4b5268);
  font-size: 0.75rem;
}

.ai-subagent-presence__details > div {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 0.5rem;
}

.ai-subagent-presence__details dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}

.ai-subagent-presence__spinner {
  color: var(--color-primary-600, #4f46e5);
  animation: ai-subagent-spin 0.9s linear infinite;
}

@keyframes ai-subagent-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-subagent-presence__spinner {
    animation: none;
  }

  .ai-subagent-presence__chevron {
    transition: none;
  }
}
</style>
