<template>
  <section class="runtime-ops-shell" data-testid="runtime-ops-shell">
    <header class="runtime-ops-header">
      <div>
        <p class="runtime-ops-kicker">Runtime Ops</p>
        <h1>运行观测</h1>
      </div>
      <a-tag color="blue">runtime_ops:read</a-tag>
    </header>

    <a-tabs v-model:activeKey="activeTab" class="runtime-ops-tabs">
      <a-tab-pane key="runs" tab="Runs">
        <section class="runtime-ops-panel" data-testid="runtime-ops-run-list">
          <form class="runtime-ops-filters" @submit.prevent="loadRuns">
            <label>
              <span>Owner</span>
              <select v-model="filters.ownerType" data-testid="runtime-ops-owner-filter">
                <option value="">全部</option>
                <option v-for="item in runtimeOpsOwnerTypeOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </option>
              </select>
            </label>
            <label>
              <span>State</span>
              <select v-model="filters.state" data-testid="runtime-ops-state-filter">
                <option value="">全部</option>
                <option v-for="item in runtimeOpsStateOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Tenant</span>
              <input v-model="filters.tenantId" data-testid="runtime-ops-tenant-filter" />
            </label>
            <label>
              <span>From</span>
              <input v-model="filters.createdFrom" type="datetime-local" />
            </label>
            <label>
              <span>To</span>
              <input v-model="filters.createdTo" type="datetime-local" />
            </label>
            <button type="submit" data-testid="runtime-ops-apply-filters">筛选</button>
          </form>

          <div class="runtime-ops-list-meta">Total {{ runList.total }}</div>
          <table class="runtime-ops-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Owner</th>
                <th>State</th>
                <th>Tenant</th>
                <th>Queue</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="run in runList.items"
                :key="run.runId"
                class="runtime-ops-run-row"
                :class="{ selected: selectedRun?.runId === run.runId }"
                data-testid="runtime-ops-run-row"
                tabindex="0"
                @click="selectRun(run)"
                @keyup.enter="selectRun(run)"
              >
                <td>#{{ run.runId }}</td>
                <td>
                  <strong>{{ run.ownerLabel }}</strong>
                  <span>{{ run.ownerTypeLabel }} #{{ run.ownerId }}</span>
                </td>
                <td>{{ run.stateLabel }}</td>
                <td>{{ run.tenantId }}</td>
                <td>{{ run.queueState }}</td>
                <td>{{ run.updatedAt || run.createdAt }}</td>
                <td>
                  <div class="runtime-ops-actions">
                    <button
                      type="button"
                      :disabled="!canCancelRun(run)"
                      :data-testid="`runtime-ops-safe-cancel-run-${run.runId}`"
                      @click.stop="cancelRun(run.runId)"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      :disabled="run.state !== 'waiting'"
                      :data-testid="`runtime-ops-safe-resume-run-${run.runId}`"
                      @click.stop="resumeRun(run.runId)"
                    >
                      Resume
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="selectedRun" class="runtime-ops-realtime-status" data-testid="runtime-ops-realtime-status">
            <span>{{ realtimeLabel }}</span>
            <strong>seq {{ realtimeState.lastSequence }}</strong>
            <span>Reconnects {{ realtimeState.reconnects }}</span>
            <em>{{ realtimeState.latestType }}</em>
          </div>

          <section v-if="dagView" class="runtime-ops-dag" data-testid="runtime-ops-dag-view">
            <header>
              <div>
                <span>Run #{{ dagView.runId }}</span>
                <strong>{{ selectedRun?.ownerLabel }}</strong>
              </div>
              <dl>
                <div v-for="(count, key) in dagView.summary" :key="key">
                  <dt>{{ key }}</dt>
                  <dd>{{ count }}</dd>
                </div>
              </dl>
            </header>
            <div class="runtime-ops-dag-grid">
              <article
                v-for="node in dagView.nodes"
                :key="node.nodeKey"
                class="runtime-ops-dag-node"
                :class="[`state-${node.state}`, { selected: nodeDetail?.nodeKey === node.nodeKey }]"
                :data-testid="`runtime-ops-dag-node-${node.nodeKey}`"
                tabindex="0"
                @click="selectNode(node.nodeKey)"
                @keyup.enter="selectNode(node.nodeKey)"
              >
                <span>{{ node.nodeType }}</span>
                <strong>{{ node.name }}</strong>
                <em>{{ node.stateLabel }}</em>
                <small v-if="node.error">{{ node.error }}</small>
              </article>
            </div>
            <ul class="runtime-ops-dag-edges">
              <li v-for="edge in dagView.edges" :key="`${edge.state}-${edge.source}-${edge.target}`">
                {{ edge.state }} {{ edge.source }} → {{ edge.target }}
              </li>
            </ul>

            <aside v-if="nodeDetail" class="runtime-ops-node-detail" data-testid="runtime-ops-node-detail">
              <header>
                <div>
                  <span>{{ nodeDetail.nodeType }} · {{ nodeDetail.status }}</span>
                  <strong>{{ nodeDetail.name }}</strong>
                </div>
                <em>{{ nodeDetail.durationLabel }}</em>
              </header>
              <dl class="runtime-ops-node-fields">
                <div>
                  <dt>Input</dt>
                  <dd>{{ nodeDetail.inputSummary }}</dd>
                </div>
                <div>
                  <dt>Output</dt>
                  <dd>{{ nodeDetail.outputSummary }}</dd>
                </div>
                <div v-if="nodeDetail.errorSummary">
                  <dt>Error</dt>
                  <dd>{{ nodeDetail.errorSummary }}</dd>
                </div>
              </dl>
              <ol class="runtime-ops-node-events">
                <li v-for="event in nodeDetail.events" :key="event.key">
                  <span>{{ event.sequenceLabel }}</span>
                  <strong>{{ event.eventType }}</strong>
                  <em>{{ event.detail }}</em>
                </li>
              </ol>
            </aside>
          </section>
        </section>
      </a-tab-pane>
      <a-tab-pane key="jobs" tab="Jobs">
        <section class="runtime-ops-panel" data-testid="runtime-ops-jobs">
          <form class="runtime-ops-filters" @submit.prevent="loadJobs">
            <label>
              <span>Owner</span>
              <select v-model="jobFilters.ownerType" data-testid="runtime-ops-job-owner-filter">
                <option value="">全部</option>
                <option v-for="item in runtimeOpsOwnerTypeOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Status</span>
              <select v-model="jobFilters.status" data-testid="runtime-ops-job-status-filter">
                <option value="">全部</option>
                <option v-for="item in runtimeOpsJobStatusOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Tenant</span>
              <input v-model="jobFilters.tenantId" data-testid="runtime-ops-job-tenant-filter" />
            </label>
            <button type="submit" data-testid="runtime-ops-job-refresh">刷新</button>
          </form>

          <div class="runtime-ops-list-meta">Total {{ jobList.total }}</div>
          <table class="runtime-ops-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Worker</th>
                <th>Attempts</th>
                <th>Next Retry</th>
                <th>Error</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in jobList.items" :key="job.jobId" class="runtime-ops-job-row" data-testid="runtime-ops-job-row">
                <td>
                  #{{ job.jobId }}
                  <span>Run #{{ job.runId }}</span>
                </td>
                <td>
                  <strong>{{ job.ownerTypeLabel }}</strong>
                  <span>#{{ job.ownerId }} · {{ job.tenantId }}</span>
                </td>
                <td>{{ job.statusLabel }}</td>
                <td>
                  {{ job.leaseOwner }}
                  <span>Heartbeat {{ job.heartbeatLabel }}</span>
                  <span>Lease {{ job.leaseExpiresAt || '-' }}</span>
                </td>
                <td>{{ job.attemptLabel }}</td>
                <td>{{ job.nextRetryLabel }}</td>
                <td>{{ job.lastError || '-' }}</td>
                <td>
                  <div class="runtime-ops-actions">
                    <button
                      type="button"
                      :disabled="job.status !== 'FAILED'"
                      :data-testid="`runtime-ops-safe-retry-job-${job.jobId}`"
                      @click="retryJob(job.jobId)"
                    >
                      Retry
                    </button>
                    <button
                      type="button"
                      :disabled="job.status !== 'IGNORED' && job.status !== 'RESOLVED'"
                      :data-testid="`runtime-ops-safe-reopen-dlq-${job.jobId}`"
                      @click="reopenDlqJob(job.jobId)"
                    >
                      Reopen
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </a-tab-pane>
      <a-tab-pane key="dlq" tab="DLQ">
        <section class="runtime-ops-panel" data-testid="runtime-ops-dlq">
          <div class="runtime-ops-list-meta">Total {{ dlqList.total }}</div>
          <table class="runtime-ops-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Error</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in dlqList.items" :key="job.jobId" class="runtime-ops-dlq-row" data-testid="runtime-ops-dlq-row">
                <td>
                  #{{ job.jobId }}
                  <span>Run #{{ job.runId }}</span>
                </td>
                <td>
                  <strong>{{ job.ownerTypeLabel }}</strong>
                  <span>#{{ job.ownerId }} · {{ job.tenantId }}</span>
                </td>
                <td>{{ job.statusLabel }}</td>
                <td>{{ job.attemptLabel }}</td>
                <td>{{ job.lastError }}</td>
                <td>{{ job.updatedAt }}</td>
                <td>
                  <div class="runtime-ops-actions">
                    <button
                      type="button"
                      :disabled="!job.canRetry"
                      :data-testid="`runtime-ops-dlq-retry-${job.jobId}`"
                      @click="retryDlq(job.jobId)"
                    >
                      Retry
                    </button>
                    <button
                      type="button"
                      :disabled="!job.canIgnore"
                      :data-testid="`runtime-ops-dlq-ignore-${job.jobId}`"
                      @click="ignoreDlq(job.jobId)"
                    >
                      Ignore
                    </button>
                    <button
                      type="button"
                      :disabled="!job.canMarkResolved"
                      :data-testid="`runtime-ops-dlq-resolve-${job.jobId}`"
                      @click="markDlqResolved(job.jobId)"
                    >
                      Resolved
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </a-tab-pane>
      <a-tab-pane key="stats" tab="Stats">
        <section class="runtime-ops-panel" data-testid="runtime-ops-stats">
          <header class="runtime-ops-section-heading">
            <div>
              <span>Selected Run</span>
              <strong>{{ selectedRun ? `#${selectedRun.runId} ${selectedRun.ownerLabel}` : 'No run selected' }}</strong>
            </div>
            <button type="button" @click="loadStatsData">刷新</button>
          </header>

          <div class="runtime-ops-stat-grid">
            <article
              v-for="stat in statsView.callStats"
              :key="stat.kind"
              class="runtime-ops-stat"
              :data-testid="`runtime-ops-stat-${stat.kind}`"
            >
              <span>{{ stat.label }}</span>
              <strong>{{ stat.total }}</strong>
              <dl>
                <div>
                  <dt>Failed</dt>
                  <dd>{{ stat.failed }}</dd>
                </div>
                <div>
                  <dt>Retries</dt>
                  <dd>{{ stat.retries }}</dd>
                </div>
              </dl>
            </article>
          </div>

          <section class="runtime-ops-failure-panel">
            <header>
              <strong>Failures & Retries</strong>
              <span>Total {{ statsView.failureItems.length }}</span>
            </header>
            <table class="runtime-ops-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Retry</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in statsView.failureItems" :key="item.key" data-testid="runtime-ops-failure-row">
                  <td>
                    {{ item.sourceLabel }}
                    <span>{{ item.kindLabel }}</span>
                  </td>
                  <td>{{ item.target }}</td>
                  <td>{{ item.status }}</td>
                  <td>{{ item.retryLabel }}</td>
                  <td>{{ item.message || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </section>
      </a-tab-pane>
    </a-tabs>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import {
  cancelRuntimeOpsRun,
  getRuntimeOpsRun,
  ignoreRuntimeOpsDlqJob,
  listRuntimeOpsJobs,
  listRuntimeOpsDlq,
  listRuntimeOpsRunEvents,
  listRuntimeOpsRunNodes,
  listRuntimeOpsRuns,
  markRuntimeOpsDlqJobResolved,
  reopenRuntimeOpsDlqJob,
  resumeRuntimeOpsRun,
  retryRuntimeOpsDlqJob,
} from '@/api/runtimeOps'

import { buildRuntimeOpsDagView, type RuntimeOpsDagView } from './runtimeOpsDag'
import { normalizeRuntimeOpsDlqList, type RuntimeOpsDlqListViewModel } from './runtimeOpsDlq'
import {
  openRuntimeOpsEventStream,
  type RuntimeOpsEventStream,
  type RuntimeOpsEventStreamStatus,
  type RuntimeOpsRealtimeEvent,
} from './runtimeOpsEventStream'
import {
  buildRuntimeOpsJobListQuery,
  normalizeRuntimeOpsJobList,
  runtimeOpsJobStatusOptions,
  type RuntimeOpsJobFilters,
  type RuntimeOpsJobListViewModel,
} from './runtimeOpsJobs'
import { buildRuntimeOpsNodeDetail, type RuntimeOpsNodeDetailView } from './runtimeOpsNodeDetail'
import { buildRuntimeOpsSafeActionConfirmMessage, type RuntimeOpsSafeAction } from './runtimeOpsSafeActions'
import { buildRuntimeOpsStatsView } from './runtimeOpsStats'
import {
  buildRuntimeOpsRunListQuery,
  normalizeRuntimeOpsRunList,
  runtimeOpsOwnerTypeOptions,
  runtimeOpsStateOptions,
  type RuntimeOpsRunFilters,
  type RuntimeOpsRunListViewModel,
} from './runtimeOpsRuns'

const activeTab = ref('runs')
const filters = reactive<RuntimeOpsRunFilters>({ page: 1, pageSize: 20 })
const runList = ref<RuntimeOpsRunListViewModel>({ items: [], total: 0 })
const jobFilters = reactive<RuntimeOpsJobFilters>({ page: 1, pageSize: 20 })
const jobList = ref<RuntimeOpsJobListViewModel>({ items: [], total: 0 })
const dlqList = ref<RuntimeOpsDlqListViewModel>({ items: [], total: 0 })
const selectedRun = ref<RuntimeOpsRunListViewModel['items'][number] | null>(null)
const dagView = ref<RuntimeOpsDagView | null>(null)
const nodeRows = ref<Record<string, any>[]>([])
const eventRows = ref<Record<string, any>[]>([])
const nodeDetail = ref<RuntimeOpsNodeDetailView | null>(null)
let realtimeStream: RuntimeOpsEventStream | null = null
const realtimeState = reactive({
  state: 'closed',
  lastSequence: 0,
  reconnects: 0,
  latestType: '-',
  error: '',
})
const statsView = computed(() =>
  buildRuntimeOpsStatsView({
    nodes: nodeRows.value,
    events: eventRows.value,
    jobs: jobList.value.items,
    dlq: dlqList.value.items,
  }),
)
const realtimeLabel = computed(() => {
  if (realtimeState.error) return 'Realtime degraded'
  if (realtimeState.state === 'open') return 'Realtime live'
  if (realtimeState.state === 'reconnecting') return 'Realtime reconnecting'
  if (realtimeState.state === 'connecting') return 'Realtime connecting'
  return 'Realtime closed'
})

onMounted(() => {
  void loadRuns()
})

onBeforeUnmount(() => {
  closeRealtimeStream()
})

watch(activeTab, (tab) => {
  if (tab === 'jobs') void loadJobs()
  if (tab === 'dlq') void loadDlq()
  if (tab === 'stats') void loadStatsData()
})

async function loadRuns() {
  const response = await listRuntimeOpsRuns(buildRuntimeOpsRunListQuery(filters))
  runList.value = normalizeRuntimeOpsRunList(response)
}

async function loadJobs() {
  const response = await listRuntimeOpsJobs(buildRuntimeOpsJobListQuery(jobFilters))
  jobList.value = normalizeRuntimeOpsJobList(response)
}

async function loadDlq() {
  const response = await listRuntimeOpsDlq({ page: 1, pageSize: 20 })
  dlqList.value = normalizeRuntimeOpsDlqList(response)
}

async function loadStatsData() {
  await Promise.all([loadJobs(), loadDlq()])
  if (!selectedRun.value && runList.value.items.length > 0) {
    await selectRun(runList.value.items[0])
  }
}

function confirmSafeAction(action: RuntimeOpsSafeAction, targetId: number) {
  return window.confirm(buildRuntimeOpsSafeActionConfirmMessage(action, targetId))
}

function canCancelRun(run: RuntimeOpsRunListViewModel['items'][number]) {
  return !['succeeded', 'failed', 'cancelled'].includes(run.state)
}

async function cancelRun(runId: number) {
  if (!confirmSafeAction('cancelRun', runId)) return
  await cancelRuntimeOpsRun(runId)
  await loadRuns()
}

async function resumeRun(runId: number) {
  if (!confirmSafeAction('resumeRun', runId)) return
  await resumeRuntimeOpsRun(runId)
  await loadRuns()
}

async function retryJob(jobId: number) {
  if (!confirmSafeAction('retryJob', jobId)) return
  await retryRuntimeOpsDlqJob(jobId)
  await loadJobs()
}

async function reopenDlqJob(jobId: number) {
  if (!confirmSafeAction('reopenDlq', jobId)) return
  await reopenRuntimeOpsDlqJob(jobId)
  await loadJobs()
}

async function retryDlq(jobId: number) {
  if (!confirmSafeAction('retryJob', jobId)) return
  await retryRuntimeOpsDlqJob(jobId)
  await loadDlq()
}

async function ignoreDlq(jobId: number) {
  if (!window.confirm(`Confirm ignore DLQ job #${jobId}?`)) return
  await ignoreRuntimeOpsDlqJob(jobId)
  await loadDlq()
}

async function markDlqResolved(jobId: number) {
  if (!window.confirm(`Confirm mark resolved DLQ job #${jobId}?`)) return
  await markRuntimeOpsDlqJobResolved(jobId)
  await loadDlq()
}

async function selectRun(run: RuntimeOpsRunListViewModel['items'][number]) {
  selectedRun.value = run
  nodeDetail.value = null
  const [latestRun, nodePage, eventPage] = await Promise.all([
    getRuntimeOpsRun(run.runId),
    listRuntimeOpsRunNodes(run.runId),
    listRuntimeOpsRunEvents(run.runId, { afterSequence: 0 }),
  ])
  selectedRun.value = {
    ...run,
    status: String(latestRun.status || run.status),
    state: String(latestRun.state || run.state),
  }
  nodeRows.value = nodePage.list || []
  eventRows.value = eventPage.list || []
  dagView.value = buildRuntimeOpsDagView({ runId: run.runId, nodes: nodeRows.value })
  startRealtimeStream(run.runId, maxEventSequence(eventRows.value))
}

function selectNode(nodeKey: string) {
  const node = nodeRows.value.find((item) => String(item.nodeKey || item.node_key || '') === nodeKey)
  if (!node) return
  nodeDetail.value = buildRuntimeOpsNodeDetail({ node, events: eventRows.value })
}

function startRealtimeStream(runId: number, afterSequence: number) {
  closeRealtimeStream()
  Object.assign(realtimeState, {
    state: 'connecting',
    lastSequence: afterSequence,
    reconnects: 0,
    latestType: '-',
    error: '',
  })
  realtimeStream = openRuntimeOpsEventStream(runId, {
    afterSequence,
    reconnectDelayMs: 3000,
    onEvent: mergeRealtimeEvent,
    onStatus: applyRealtimeStatus,
    onError: (error) => {
      realtimeState.error = error.message
    },
  })
}

function closeRealtimeStream() {
  realtimeStream?.close()
  realtimeStream = null
}

function applyRealtimeStatus(status: RuntimeOpsEventStreamStatus) {
  realtimeState.state = status.state
  realtimeState.lastSequence = status.lastSequence
  realtimeState.reconnects = status.reconnects
  realtimeState.latestType = status.latestType
}

function mergeRealtimeEvent(event: RuntimeOpsRealtimeEvent) {
  const sequence = Number(event.sequence || 0)
  const eventKey = String(event.id || sequence || `${event.type}:${eventRows.value.length}`)
  const nextRows = eventRows.value.filter((row) => String(row.id || row.sequence || '') !== eventKey)
  nextRows.push(event)
  eventRows.value = nextRows.sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0))
  applyRealtimeEventToNode(event)
}

function applyRealtimeEventToNode(event: RuntimeOpsRealtimeEvent) {
  const payload = event.payload && typeof event.payload === 'object' ? event.payload as Record<string, any> : {}
  const nodeKey = String(event.nodeId || payload.nodeKey || payload.nodeId || '')
  if (!nodeKey) return
  const status = statusFromRealtimeEvent(event)
  nodeRows.value = nodeRows.value.map((node) => {
    const currentNodeKey = String(node.nodeKey || node.node_key || '')
    if (currentNodeKey !== nodeKey) return node
    return {
      ...node,
      status: status || node.status,
      outputs: payload.outputs || payload.output || node.outputs,
      error: payload.error || node.error,
      selectionState: payload.selectionState || nextSelectionState(node.selectionState, status),
    }
  })
  if (selectedRun.value) {
    dagView.value = buildRuntimeOpsDagView({ runId: selectedRun.value.runId, nodes: nodeRows.value })
  }
  if (nodeDetail.value?.nodeKey === nodeKey) {
    const node = nodeRows.value.find((item) => String(item.nodeKey || item.node_key || '') === nodeKey)
    if (node) nodeDetail.value = buildRuntimeOpsNodeDetail({ node, events: eventRows.value })
  }
}

function statusFromRealtimeEvent(event: RuntimeOpsRealtimeEvent): string {
  const eventType = String(event.type || '')
  const payload = event.payload && typeof event.payload === 'object' ? event.payload as Record<string, any> : {}
  if (payload.status) return String(payload.status).toUpperCase()
  if (eventType.endsWith('_started')) return 'RUNNING'
  if (eventType.endsWith('_completed')) return 'COMPLETED'
  if (eventType.endsWith('_failed')) return 'FAILED'
  if (eventType.endsWith('_waiting')) return 'WAITING'
  if (eventType.endsWith('_skipped')) return 'SKIPPED'
  return ''
}

function nextSelectionState(selectionState: unknown, status: string): unknown {
  if (!selectionState || typeof selectionState !== 'object' || !status) return selectionState
  return { ...(selectionState as Record<string, any>), state: status.toLowerCase() }
}

function maxEventSequence(events: Record<string, any>[]): number {
  return events.reduce((max, event) => Math.max(max, Number(event.sequence || 0)), 0)
}
</script>

<style scoped>
.runtime-ops-shell {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  gap: 1rem;
}

.runtime-ops-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}

.runtime-ops-kicker {
  margin: 0 0 0.25rem;
  color: #5b6472;
  font-size: 0.8125rem;
  letter-spacing: 0;
}

.runtime-ops-header h1 {
  margin: 0;
  color: #111827;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.25;
}

.runtime-ops-tabs {
  min-width: 0;
}

.runtime-ops-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.runtime-ops-filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
  align-items: end;
}

.runtime-ops-filters label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  color: #4b5563;
  font-size: 0.8125rem;
}

.runtime-ops-filters input,
.runtime-ops-filters select {
  min-width: 0;
  height: 2.25rem;
  border: 0.0625rem solid #d1d5db;
  border-radius: 0.375rem;
  padding: 0 0.625rem;
  color: #111827;
  font: inherit;
}

.runtime-ops-filters button {
  height: 2.25rem;
  border: 0;
  border-radius: 0.375rem;
  background: #1677ff;
  color: #fff;
  cursor: pointer;
  font: inherit;
}

.runtime-ops-list-meta {
  color: #4b5563;
  font-size: 0.8125rem;
}

.runtime-ops-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.runtime-ops-table th,
.runtime-ops-table td {
  border-bottom: 0.0625rem solid #e5e7eb;
  padding: 0.625rem 0.5rem;
  text-align: left;
  vertical-align: top;
}

.runtime-ops-table th {
  color: #4b5563;
  font-size: 0.75rem;
  font-weight: 600;
}

.runtime-ops-table td {
  color: #111827;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.runtime-ops-table td span {
  display: block;
  margin-top: 0.125rem;
  color: #6b7280;
  font-size: 0.75rem;
}

.runtime-ops-run-row {
  cursor: pointer;
}

.runtime-ops-run-row:hover,
.runtime-ops-run-row.selected {
  background: #f8fafc;
}

.runtime-ops-dag {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-top: 0.0625rem solid #e5e7eb;
  padding-top: 0.75rem;
}

.runtime-ops-dag header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.runtime-ops-dag header span,
.runtime-ops-dag header strong {
  display: block;
}

.runtime-ops-dag header span {
  color: #6b7280;
  font-size: 0.75rem;
}

.runtime-ops-dag header strong {
  color: #111827;
  font-size: 1rem;
}

.runtime-ops-dag dl {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0;
}

.runtime-ops-dag dl div {
  min-width: 4.5rem;
}

.runtime-ops-dag dt,
.runtime-ops-dag dd {
  margin: 0;
}

.runtime-ops-dag dt {
  color: #6b7280;
  font-size: 0.6875rem;
  text-transform: uppercase;
}

.runtime-ops-dag dd {
  color: #111827;
  font-size: 1rem;
  font-weight: 700;
}

.runtime-ops-dag-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.625rem;
}

.runtime-ops-dag-node {
  min-width: 0;
  border: 0.0625rem solid #d1d5db;
  border-left-width: 0.25rem;
  border-radius: 0.5rem;
  padding: 0.625rem;
  background: #fff;
  cursor: pointer;
}

.runtime-ops-dag-node span,
.runtime-ops-dag-node strong,
.runtime-ops-dag-node em,
.runtime-ops-dag-node small {
  display: block;
}

.runtime-ops-dag-node span {
  color: #6b7280;
  font-size: 0.6875rem;
}

.runtime-ops-dag-node strong {
  margin-top: 0.125rem;
  color: #111827;
  font-size: 0.875rem;
}

.runtime-ops-dag-node em {
  margin-top: 0.375rem;
  color: #374151;
  font-size: 0.8125rem;
  font-style: normal;
}

.runtime-ops-dag-node small {
  margin-top: 0.25rem;
  color: #b91c1c;
  font-size: 0.75rem;
}

.runtime-ops-dag-node.state-completed {
  border-left-color: #16a34a;
}

.runtime-ops-dag-node.state-skipped {
  border-left-color: #94a3b8;
}

.runtime-ops-dag-node.state-running {
  border-left-color: #1677ff;
}

.runtime-ops-dag-node.state-waiting {
  border-left-color: #d97706;
}

.runtime-ops-dag-node.state-failed {
  border-left-color: #dc2626;
}

.runtime-ops-dag-node.selected {
  background: #f8fafc;
  box-shadow: 0 0 0 0.125rem rgba(22, 119, 255, 0.12);
}

.runtime-ops-dag-edges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.runtime-ops-dag-edges li {
  border-radius: 999rem;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

.runtime-ops-node-detail {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border: 0.0625rem solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 0.75rem;
  background: #fff;
}

.runtime-ops-node-detail header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.runtime-ops-node-detail header span,
.runtime-ops-node-detail header strong,
.runtime-ops-node-detail header em {
  display: block;
}

.runtime-ops-node-detail header span {
  color: #6b7280;
  font-size: 0.75rem;
}

.runtime-ops-node-detail header strong {
  color: #111827;
  font-size: 1rem;
}

.runtime-ops-node-detail header em {
  color: #374151;
  font-size: 0.875rem;
  font-style: normal;
}

.runtime-ops-node-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.75rem;
  margin: 0;
}

.runtime-ops-node-fields dt,
.runtime-ops-node-fields dd {
  margin: 0;
}

.runtime-ops-node-fields dt {
  color: #6b7280;
  font-size: 0.75rem;
  font-weight: 600;
}

.runtime-ops-node-fields dd {
  margin-top: 0.25rem;
  color: #111827;
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}

.runtime-ops-node-events {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.runtime-ops-node-events li {
  display: grid;
  grid-template-columns: 3.5rem minmax(12rem, 1fr) minmax(12rem, 2fr);
  gap: 0.5rem;
  border-bottom: 0.0625rem solid #f1f5f9;
  padding-bottom: 0.375rem;
  color: #111827;
  font-size: 0.8125rem;
}

.runtime-ops-node-events span {
  color: #6b7280;
}

.runtime-ops-node-events em {
  color: #4b5563;
  font-style: normal;
  overflow-wrap: anywhere;
}

.runtime-ops-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.runtime-ops-actions button {
  border: 0.0625rem solid #d1d5db;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  background: #fff;
  color: #111827;
  cursor: pointer;
  font: inherit;
}

.runtime-ops-actions button:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.runtime-ops-realtime-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  border: 0.0625rem solid #dbeafe;
  border-radius: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: 0.8125rem;
}

.runtime-ops-realtime-status strong,
.runtime-ops-realtime-status em {
  font-style: normal;
  font-weight: 600;
}

.runtime-ops-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.runtime-ops-section-heading span,
.runtime-ops-section-heading strong {
  display: block;
}

.runtime-ops-section-heading span {
  color: #6b7280;
  font-size: 0.75rem;
}

.runtime-ops-section-heading strong {
  color: #111827;
  font-size: 1rem;
}

.runtime-ops-section-heading button {
  border: 0.0625rem solid #d1d5db;
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: #fff;
  color: #111827;
  cursor: pointer;
  font: inherit;
}

.runtime-ops-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}

.runtime-ops-stat {
  min-width: 0;
  border: 0.0625rem solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 0.75rem;
  background: #fff;
}

.runtime-ops-stat span,
.runtime-ops-stat strong {
  display: block;
}

.runtime-ops-stat span {
  color: #6b7280;
  font-size: 0.75rem;
}

.runtime-ops-stat strong {
  margin-top: 0.25rem;
  color: #111827;
  font-size: 1.5rem;
  line-height: 1.2;
}

.runtime-ops-stat dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0.75rem 0 0;
}

.runtime-ops-stat dt,
.runtime-ops-stat dd {
  margin: 0;
}

.runtime-ops-stat dt {
  color: #6b7280;
  font-size: 0.6875rem;
  text-transform: uppercase;
}

.runtime-ops-stat dd {
  color: #111827;
  font-size: 0.9375rem;
  font-weight: 700;
}

.runtime-ops-failure-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.runtime-ops-failure-panel header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
}

.runtime-ops-failure-panel header strong {
  color: #111827;
  font-size: 1rem;
}

.runtime-ops-failure-panel header span {
  color: #6b7280;
  font-size: 0.75rem;
}
</style>
