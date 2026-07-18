<template>
  <article
    class="ai-activity-row"
    :class="`status-${activity.status}`"
    data-testid="ai-assistant-activity-row"
  >
    <div class="ai-activity-row__rail" aria-hidden="true">
      <span class="ai-activity-row__status">
        <LoadingOutlined v-if="activity.status === 'running'" class="ai-activity-row__spinner" />
        <CheckCircleOutlined v-else-if="activity.status === 'completed'" />
        <ExclamationCircleOutlined v-else-if="activity.status === 'failed'" />
        <StopOutlined v-else-if="activity.status === 'cancelled'" />
        <ClockCircleOutlined v-else />
      </span>
    </div>
    <div class="ai-activity-row__content">
      <button
        class="ai-activity-row__header"
        type="button"
        data-testid="ai-assistant-activity-toggle"
        :aria-expanded="expanded"
        :aria-controls="detailId"
        @click="$emit('toggle')"
      >
        <strong class="ai-activity-row__title">{{ activity.title }}</strong>
        <small class="ai-activity-row__summary">{{ activity.summary }}</small>
        <small class="ai-activity-row__meta">
          {{ statusLabel }} · {{ activityElapsedLabel(activity, nowMs) }}
          <AiAssistantActivityProgress v-if="progress" :progress="progress" />
        </small>
        <RightOutlined
          class="ai-collapse-chevron"
          aria-hidden="true"
          :class="{ expanded }"
        />
      </button>
      <section
        v-if="expanded"
        :id="detailId"
        class="ai-activity-row__details"
        data-testid="ai-assistant-activity-details"
      >
        <slot />
        <dl class="ai-activity-row__audit">
          <div>
            <dt>事件范围</dt>
            <dd>#{{ activity.firstSequence }}–#{{ activity.lastSequence }}</dd>
          </div>
          <div v-if="auditReference">
            <dt>审计引用</dt>
            <dd>{{ auditReference }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  RightOutlined,
  StopOutlined,
} from '@ant-design/icons-vue'
import { computed } from 'vue'

import type { RunActivity } from './aiAssistantActivity'
import type { RunActivityProgress } from './aiAssistantActivityView'
import { activityElapsedLabel } from './aiAssistantActivityView'
import AiAssistantActivityProgress from './AiAssistantActivityProgress.vue'

const props = defineProps<{
  activity: RunActivity
  expanded: boolean
  nowMs: number
  progress?: RunActivityProgress
}>()

defineEmits<{
  toggle: []
}>()

const detailId = computed(() => `ai-activity-${props.activity.runId}-${safeId(props.activity.id)}`)
const statusLabel = computed(() => ({
  queued: '等待执行',
  running: '执行中',
  waiting_approval: '等待审批',
  completed: '已完成',
  failed: '执行失败',
  cancelled: '已取消',
})[props.activity.status])
const auditReference = computed(() => [
  props.activity.statusRef,
  props.activity.resultRef,
  props.activity.eventStreamRef,
].filter(Boolean).join(' · '))

function safeId(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]/g, '-')
}
</script>

<style scoped>
.ai-activity-row {
  position: relative;
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: 0.5rem;
  min-width: 0;
}

.ai-activity-row__rail {
  position: relative;
  display: flex;
  justify-content: center;
  padding-top: 0.8125rem;
}

.ai-activity-row:not(:last-child) .ai-activity-row__rail::after {
  content: '';
  position: absolute;
  top: 1.875rem;
  bottom: -0.625rem;
  width: 0.0625rem;
  background: var(--color-border-default, #e3e6ef);
}

.ai-activity-row__status {
  position: relative;
  z-index: 1;
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.875rem;
}

.status-running .ai-activity-row__status {
  color: var(--color-primary-600, #4f46e5);
}

.status-completed .ai-activity-row__status {
  color: var(--color-success-500, #10b981);
}

.status-waiting_approval .ai-activity-row__status {
  color: var(--color-warning-600, #d97706);
}

.status-failed .ai-activity-row__status,
.status-cancelled .ai-activity-row__status {
  color: var(--color-danger-500, #ef4444);
}

.ai-activity-row__content {
  min-width: 0;
  padding: 0.375rem 0 0.625rem;
}

.ai-activity-row__header {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 0.5rem;
  align-items: center;
  justify-content: start;
  justify-items: start;
  padding: 0.375rem 0.5rem;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
  cursor: pointer;
}

.ai-activity-row__header:hover,
.ai-activity-row__header:focus-visible {
  background: var(--color-bg-hover, #f1f2f7);
}

.ai-activity-row__header:focus-visible {
  outline: 0.125rem solid var(--color-border-focus, #6366f1);
  outline-offset: 0.125rem;
}

.ai-activity-row__title,
.ai-activity-row__summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-activity-row__title {
  font-size: 0.9375rem;
  line-height: 1.25;
}

.ai-activity-row__summary,
.ai-activity-row__meta {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  line-height: 1.25;
  white-space: nowrap;
}

.ai-collapse-chevron {
  width: 0.75rem;
  height: 0.75rem;
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.625rem;
  transform: rotate(0deg);
  transition: transform 0.16s ease;
}

.ai-collapse-chevron.expanded {
  transform: rotate(90deg);
}

.ai-activity-row__details {
  display: grid;
  gap: 0.625rem;
  padding: 0.375rem 0.5rem 0.25rem;
}

.ai-activity-row__audit {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
}

.ai-activity-row__audit > div {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 0.5rem;
}

.ai-activity-row__audit dt {
  font-weight: 600;
}

.ai-activity-row__audit dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}

.ai-activity-row__spinner {
  animation: ai-activity-spin 0.9s linear infinite;
}

@keyframes ai-activity-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-activity-row__spinner {
    animation: none;
  }

  .ai-collapse-chevron {
    transition: none;
  }
}
</style>
