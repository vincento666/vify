<template>
  <section class="run-records-panel">
    <div class="records-header">
      <label class="filter-field">
        <span class="filter-label">运行状态</span>
        <a-select
          v-model:value="statusFilter"
          class="status-filter"
          size="small"
          data-testid="run-status-filter"
          @change="loadRuns"
        >
          <a-select-option v-for="option in statusOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </a-select-option>
        </a-select>
      </label>
    </div>

    <div v-if="runs.length === 0 && !loading" class="empty-panel compact">
      <h3>暂无运行记录</h3>
      <p>实验运行后会在这里沉淀报告入口和失败诊断线索。</p>
    </div>

    <section v-if="activeRun" class="report-panel">
      <div class="report-summary">
        <div class="report-title">
          <div class="report-title-line">
            <h3>运行 #{{ activeRun.id }}</h3>
            <a-tag :color="runStatusColor(activeRun.status)">{{ activeRun.status }}</a-tag>
          </div>
          <p>{{ failureInvestigationTitle(activeRun.failedCases) }}</p>
        </div>
        <div class="summary-metrics">
          <div v-for="metric in runSummaryMetricItems(activeRun)" :key="metric.label" class="metric-item">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
        <a-button size="small" data-testid="export-run-csv" @click="exportCsv">导出 CSV</a-button>
      </div>

      <div class="report-controls">
        <label class="filter-field">
          <span class="filter-label">用例范围</span>
          <a-select
            :key="`${activeRun.id}-${caseFilter}`"
            v-model:value="caseFilter"
            class="case-filter"
            size="small"
            data-testid="case-status-filter"
            @change="reloadActiveRun"
          >
            <a-select-option v-for="option in caseFilterOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </a-select-option>
          </a-select>
        </label>
      </div>

      <a-table v-if="visibleCases.length > 0" row-key="id" :data-source="visibleCases" bordered>
        <a-table-column title="输入" width="13.75rem" ellipsis>
          <template #default="{ record: row }">
            <div class="case-input-cell">
              <a-tag :color="row.status === 'FAILED' ? 'error' : 'success'">{{ row.status }}</a-tag>
              <span>{{ row.input }}</span>
            </div>
          </template>
        </a-table-column>
        <a-table-column data-index="expectedOutput" title="期望输出" width="11.25rem" ellipsis />
        <a-table-column title="目标输出" width="16.25rem" ellipsis>
          <template #default="{ record: row }">
            <div class="target-output-cell">
              <span>{{ row.targetOutput }}</span>
              <a
                v-if="targetEvidenceActionLabel(row)"
                class="target-evidence-link"
                data-testid="target-debug-link"
                :href="targetEvidenceHref(row)"
              >
                {{ targetEvidenceActionLabel(row) }}
              </a>
            </div>
          </template>
        </a-table-column>
        <a-table-column data-index="reason" title="评估器原因" width="15rem" ellipsis />
        <a-table-column title="操作" width="8.125rem" fixed="right">
          <template #default="{ record: row }">
            <div class="case-actions">
              <a-button
                type="link"
                size="small"
                data-testid="rerun-case-result"
                :loading="rerunningCaseId === row.id"
                @click="rerunCase(row)"
              >
                {{ rerunActionLabel(row) }}
              </a-button>
            </div>
          </template>
        </a-table-column>
      </a-table>

      <div v-else class="case-empty">
        <h3>没有匹配的用例</h3>
        <p>切换筛选条件查看其它结果。</p>
      </div>
    </section>

    <div v-if="runs.length > 0" class="run-grid">
      <article v-for="run in runs" :key="run.id" class="run-card">
        <div>
          <div class="card-title-row">
            <h4>运行 #{{ run.id }}</h4>
            <a-tag :color="runStatusColor(run.status)">{{ run.status }}</a-tag>
          </div>
          <p>实验 #{{ run.experimentId }}</p>
          <p>{{ run.totalCases }} 条用例 · {{ run.failedCases }} 失败</p>
        </div>
        <a-button type="link" size="small" @click="openReport(run)">查看报告</a-button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  exportEvaluationRunCsv,
  getEvaluationRun,
  listEvaluationRuns,
  rerunEvaluationCaseResult,
  type EvaluationCaseResult,
  type EvaluationRun,
} from '@/api/evaluation'
import { runStatusTone, runSummaryMetricItems } from './experimentRunViewModel'
import {
  failureInvestigationTitle,
  filterCaseResults,
  rerunActionLabel,
  targetEvidenceActionLabel,
  targetEvidenceHref,
} from './runReportViewModel'

const statusOptions = [
  { label: '全部', value: 'ALL' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '失败', value: 'FAILED' },
]
const caseFilterOptions = [
  { label: '全部用例', value: 'ALL' },
  { label: '失败用例', value: 'FAILED' },
  { label: '通过用例', value: 'PASSED' },
]

const runs = ref<EvaluationRun[]>([])
const activeRun = ref<EvaluationRun | null>(null)
const loading = ref(false)
const statusFilter = ref('ALL')
const caseFilter = ref<'ALL' | 'FAILED' | 'PASSED'>('ALL')
const rerunningCaseId = ref<number | null>(null)
const pageSize = 20

const visibleCases = computed<EvaluationCaseResult[]>(() => {
  if (!activeRun.value) return []
  return filterCaseResults(activeRun.value.caseResults, caseFilter.value)
})

onMounted(loadRuns)

function runStatusColor(status: string) {
  const tone = runStatusTone(status)
  return tone === 'danger' ? 'error' : tone
}

async function loadRuns() {
  loading.value = true
  try {
    const result = await listEvaluationRuns({
      page: 1,
      pageSize,
      status: statusFilter.value === 'ALL' ? undefined : statusFilter.value,
    })
    runs.value = result.list
  } finally {
    loading.value = false
  }
}

async function openReport(run: EvaluationRun) {
  caseFilter.value = run.failedCases > 0 ? 'FAILED' : 'ALL'
  activeRun.value = await getEvaluationRun(run.id, caseFilter.value === 'ALL' ? undefined : { caseStatus: caseFilter.value })
}

async function reloadActiveRun() {
  if (!activeRun.value) return
  activeRun.value = await getEvaluationRun(
    activeRun.value.id,
    caseFilter.value === 'ALL' ? undefined : { caseStatus: caseFilter.value },
  )
}

async function rerunCase(caseResult: EvaluationCaseResult) {
  if (!activeRun.value) return
  rerunningCaseId.value = caseResult.id
  try {
    const rerun = await rerunEvaluationCaseResult(activeRun.value.id, caseResult.id)
    caseFilter.value = 'ALL'
    activeRun.value = rerun
    await loadRuns()
  } finally {
    rerunningCaseId.value = null
  }
}

async function exportCsv() {
  if (!activeRun.value) return
  const blob = await exportEvaluationRunCsv(activeRun.value.id)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `evaluation-run-${activeRun.value.id}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.run-records-panel {
  padding-top: 0.125rem;
}

.records-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin: 0.875rem 0;
}

.status-filter {
  width: 10rem;
}

.filter-field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-label {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  white-space: nowrap;
}

.status-filter {
  flex-shrink: 0;
}

.run-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16.25rem, 1fr));
  gap: var(--space-3);
}

.run-card {
  min-height: 8rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: 0.875rem;
  background: #fff;
}

.card-title-row,
.report-summary,
.report-title-line,
.summary-metrics {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.card-title-row,
.report-summary {
  justify-content: space-between;
}

.run-card h4,
.report-panel h3,
.case-empty h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
}

.run-card p,
.report-panel p,
.case-empty p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.compact {
  min-height: 13.75rem;
}

.report-panel {
  margin-bottom: 1rem;
  padding: 1rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: #fff;
}

.report-summary {
  flex-wrap: wrap;
}

.report-title {
  min-width: 14rem;
  flex: 1;
}

.summary-metrics strong {
  color: var(--color-primary);
  font-size: var(--text-base);
}

.metric-item {
  min-width: 5.5rem;
  padding: 0.5rem 0.75rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
}

.metric-item span {
  display: block;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.report-controls {
  display: flex;
  justify-content: flex-end;
  margin: 0.875rem 0 0.75rem;
}

.case-filter {
  width: 11rem;
  flex-shrink: 0;
}

.case-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.target-output-cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.target-output-cell span {
  white-space: normal;
  overflow-wrap: anywhere;
}

.case-input-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.case-input-cell span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
}

.target-evidence-link {
  color: var(--color-primary);
  font-size: var(--text-sm);
  text-decoration: none;
}

.target-evidence-link:hover {
  color: rgba(99, 102, 241, 0.5);
}

.case-empty {
  min-height: 8.75rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

@media (max-width: 48rem) {
  .records-header,
  .report-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-item {
    min-width: 0;
  }

  .report-controls {
    justify-content: flex-start;
  }

  .filter-field {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
