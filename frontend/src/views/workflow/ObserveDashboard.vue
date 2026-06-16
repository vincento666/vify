<template>
  <section class="observe-page">
    <header class="observe-header">
      <div>
        <h2>运行观测</h2>
        <p>Runs, sessions, handoffs, events, and trace details</p>
      </div>
      <button type="button" @click="loadObserve">刷新</button>
    </header>

    <div class="metric-grid" data-testid="observe-metrics">
      <article v-for="tile in metricTiles" :key="tile.label">
        <span>{{ tile.label }}</span>
        <strong>{{ tile.value }}</strong>
      </article>
    </div>

    <div class="observe-grid">
      <section class="observe-panel" data-testid="observe-runs">
        <div class="panel-title">
          <strong>Run List</strong>
          <span>{{ runs.length }} / {{ runTotal }}</span>
        </div>
        <button
          v-for="run in runs"
          :key="run.runId"
          type="button"
          class="run-row"
          :class="{ active: selectedRun?.runId === run.runId }"
          @click="selectRun(run.runId)"
        >
          <span>#{{ run.runId }} {{ run.workflowName }}</span>
          <em>{{ run.status }}</em>
          <small>{{ run.flowType }} · {{ run.channel || '-' }} · {{ run.userId || '-' }}</small>
        </button>
      </section>

      <section class="observe-panel" data-testid="observe-run-detail">
        <div class="panel-title">
          <strong>Trace Detail</strong>
          <span>{{ selectedRun ? `Run #${selectedRun.runId}` : '未选择' }}</span>
        </div>
        <template v-if="selectedRun">
          <dl class="detail-list">
            <div><dt>Status</dt><dd>{{ selectedRun.status }}</dd></div>
            <div><dt>Workflow</dt><dd>{{ selectedRun.workflowName }}</dd></div>
            <div><dt>Channel</dt><dd>{{ selectedRun.channel || '-' }}</dd></div>
          </dl>
          <h3>Sanitized Logs</h3>
          <div class="sanitized-log-grid">
            <article data-testid="observe-run-input">
              <strong>Input</strong>
              <pre>{{ formatJson(selectedRun.input || {}) }}</pre>
            </article>
            <article data-testid="observe-run-output">
              <strong>Output</strong>
              <pre>{{ formatJson(selectedRun.output || {}) }}</pre>
            </article>
          </div>
          <h3>Node Runs</h3>
          <ol class="trace-list">
            <li v-for="node in selectedRun.nodeRuns" :key="node.id">
              <strong>{{ node.nodeKey }}</strong>
              <span>{{ node.nodeType }} · {{ node.status }} · {{ node.elapsedMs }}ms</span>
            </li>
          </ol>
          <h3>Events</h3>
          <ol class="trace-list">
            <li v-for="event in selectedRun.events" :key="event.id">
              <strong>{{ event.type }}</strong>
              <span>{{ event.nodeKey || '-' }}</span>
              <pre v-if="event.payload" class="event-payload">{{ formatJson(event.payload) }}</pre>
            </li>
          </ol>
        </template>
        <p v-else class="empty-hint">选择一个 Run 查看调用树和事件。</p>
      </section>

      <section class="observe-panel" data-testid="observe-sessions">
        <div class="panel-title">
          <strong>Sessions</strong>
          <span>{{ sessions.length }} / {{ sessionTotal }}</span>
        </div>
        <article v-for="session in sessions" :key="session.sessionId" class="session-row">
          <strong>{{ session.conversationId }}</strong>
          <span>{{ session.status }} · {{ session.channel }} · {{ session.userId || '-' }}</span>
          <small>Run #{{ session.currentRunId }}</small>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getObserveMetrics, getObserveRun, listObserveRuns, listObserveSessions } from '@/api/observe'
import { buildObserveMetricTiles, normalizeObserveRunIdQuery } from './observeDashboard'

const route = useRoute()
const router = useRouter()
const metrics = ref<Record<string, any>>({})
const runs = ref<any[]>([])
const runTotal = ref(0)
const sessions = ref<any[]>([])
const sessionTotal = ref(0)
const selectedRun = ref<any | null>(null)

const metricTiles = computed(() => buildObserveMetricTiles(metrics.value))

onMounted(loadObserve)

async function loadObserve() {
  const [metricsResult, runsResult, sessionsResult] = await Promise.all([
    getObserveMetrics(),
    listObserveRuns({ pageSize: 20 }),
    listObserveSessions({ pageSize: 20 }),
  ])
  metrics.value = metricsResult
  runs.value = runsResult.list || []
  runTotal.value = runsResult.total || 0
  sessions.value = sessionsResult.list || []
  sessionTotal.value = sessionsResult.total || 0
  const requestedRunId = normalizeObserveRunIdQuery(route.query.runId as string | string[] | undefined)
  if (requestedRunId) {
    await selectRun(requestedRunId)
  } else if (runs.value.length) {
    await selectRun(runs.value[0].runId)
  }
}

async function selectRun(runId: number) {
  selectedRun.value = await getObserveRun(runId)
  if (normalizeObserveRunIdQuery(route.query.runId as string | string[] | undefined) !== runId) {
    await router.replace({ name: 'HifyObserve', query: { ...route.query, runId: String(runId) } })
  }
}

function formatJson(value: any) {
  return JSON.stringify(value || {}, null, 2)
}
</script>

<style scoped>
.observe-page {
  display: grid;
  gap: 1rem;
}

.observe-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.observe-header h2,
.observe-header p {
  margin: 0;
}

.observe-header p {
  color: #64748b;
}

.observe-header button {
  border: 0;
  border-radius: 0.5rem;
  background: #5d5ff6;
  color: #fff;
  padding: 0.5rem 0.875rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}

.metric-grid article,
.observe-panel {
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  background: #fff;
}

.metric-grid article {
  padding: 0.875rem;
}

.metric-grid span,
.run-row small,
.session-row span,
.session-row small,
.trace-list span {
  color: #64748b;
}

.metric-grid strong {
  display: block;
  margin-top: 0.25rem;
  font-size: 1.35rem;
}

.observe-grid {
  display: grid;
  grid-template-columns: minmax(16.25rem, 0.95fr) minmax(22.5rem, 1.4fr) minmax(16.25rem, 0.95fr);
  gap: 0.75rem;
}

.observe-panel {
  min-height: 26rem;
  padding: 0.875rem;
}

.panel-title {
  display: flex;
  justify-content: space-between;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid #edf2f7;
}

.run-row,
.session-row {
  display: grid;
  gap: 0.25rem;
  width: 100%;
  margin-top: 0.625rem;
  padding: 0.625rem;
  border: 1px solid #edf2f7;
  border-radius: 0.5rem;
  background: #fff;
  text-align: left;
}

.run-row.active {
  border-color: #5d5ff6;
  background: #f5f6ff;
}

.run-row em {
  font-style: normal;
  color: #2563eb;
}

.detail-list div {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.trace-list {
  margin: 0;
  padding-left: 1rem;
}

.trace-list li {
  margin: 0.5rem 0;
}

.sanitized-log-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.sanitized-log-grid article,
.event-payload {
  border: 1px solid #edf2f7;
  border-radius: 0.375rem;
  background: #f8fafc;
}

.sanitized-log-grid article {
  padding: 0.5rem;
}

.sanitized-log-grid pre,
.event-payload {
  max-height: 9rem;
  margin: 0.375rem 0 0;
  overflow: auto;
  color: #475569;
  white-space: pre-wrap;
}

.event-payload {
  padding: 0.5rem;
}

.empty-hint {
  color: #94a3b8;
}
</style>
