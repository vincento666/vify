<template>
  <section class="run-records-panel">
    <div class="panel-toolbar">
      <el-segmented v-model="statusFilter" :options="statusOptions" @change="loadRuns" />
    </div>

    <div v-if="runs.length === 0 && !loading" class="empty-panel compact">
      <h3>暂无运行记录</h3>
      <p>实验运行后会在这里沉淀报告入口和失败诊断线索。</p>
    </div>

    <div v-else class="run-grid">
      <article v-for="run in runs" :key="run.id" class="run-card">
        <div>
          <div class="card-title-row">
            <h4>Run #{{ run.id }}</h4>
            <el-tag :type="runStatusTone(run.status)">{{ run.status }}</el-tag>
          </div>
          <p>Experiment #{{ run.experimentId }}</p>
          <p>{{ run.totalCases }} cases · {{ run.failedCases }} failed</p>
        </div>
        <el-button type="primary" link size="small" @click="openReport(run)">查看报告</el-button>
      </article>
    </div>

    <section v-if="activeRun" class="report-panel">
      <div class="report-header">
        <div>
          <h3>Run #{{ activeRun.id }}</h3>
          <p>{{ failureInvestigationTitle(activeRun.failedCases) }}</p>
        </div>
        <div class="summary-metrics">
          <el-tag :type="runStatusTone(activeRun.status)">{{ activeRun.status }}</el-tag>
          <strong>{{ formatRunSummary(activeRun).scoreText }}</strong>
          <span>Pass {{ formatRunSummary(activeRun).passRateText }}</span>
          <span>{{ formatRunSummary(activeRun).failedText }}</span>
          <el-button size="small" data-testid="export-run-csv" @click="exportCsv">导出 CSV</el-button>
        </div>
      </div>

      <div class="case-filter">
        <el-segmented
          :key="`${activeRun.id}-${caseFilter}`"
          v-model="caseFilter"
          :options="caseFilterOptions"
          @change="reloadActiveRun"
        />
      </div>

      <el-table v-if="visibleCases.length > 0" :data="visibleCases" border>
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="input" label="输入" min-width="180" show-overflow-tooltip />
        <el-table-column prop="expectedOutput" label="期望输出" min-width="180" show-overflow-tooltip />
        <el-table-column prop="targetOutput" label="Target Output" min-width="220" show-overflow-tooltip />
        <el-table-column prop="reason" label="评估器原因" min-width="240" show-overflow-tooltip />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              data-testid="rerun-case-result"
              :loading="rerunningCaseId === row.id"
              @click="rerunCase(row)"
            >
              {{ rerunActionLabel(row) }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="case-empty">
        <h3>没有匹配的用例</h3>
        <p>切换筛选条件查看其它结果。</p>
      </div>
    </section>
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
import { formatRunSummary, runStatusTone } from './experimentRunViewModel'
import { failureInvestigationTitle, filterCaseResults, rerunActionLabel } from './runReportViewModel'

const statusOptions = [
  { label: 'All', value: '' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Failed', value: 'FAILED' },
]
const caseFilterOptions = [
  { label: 'All Cases', value: 'ALL' },
  { label: 'Failed Cases', value: 'FAILED' },
  { label: 'Passed Cases', value: 'PASSED' },
]

const runs = ref<EvaluationRun[]>([])
const activeRun = ref<EvaluationRun | null>(null)
const loading = ref(false)
const statusFilter = ref('')
const caseFilter = ref<'ALL' | 'FAILED' | 'PASSED'>('ALL')
const rerunningCaseId = ref<number | null>(null)
const pageSize = 20

const visibleCases = computed<EvaluationCaseResult[]>(() => {
  if (!activeRun.value) return []
  return filterCaseResults(activeRun.value.caseResults, caseFilter.value)
})

onMounted(loadRuns)

async function loadRuns() {
  loading.value = true
  try {
    const result = await listEvaluationRuns({
      page: 1,
      pageSize,
      status: statusFilter.value || undefined,
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
  padding-top: 2px;
}

.panel-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 14px;
}

.run-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.run-card {
  min-height: 128px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.card-title-row,
.report-header,
.summary-metrics {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title-row,
.report-header {
  justify-content: space-between;
}

.run-card h4,
.report-panel h3,
.case-empty h3 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.run-card p,
.report-panel p,
.case-empty p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.compact {
  min-height: 220px;
}

.report-panel {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.summary-metrics strong {
  color: var(--el-color-primary);
  font-size: 18px;
}

.case-filter {
  display: flex;
  justify-content: flex-end;
  margin: 14px 0;
}

.case-empty {
  min-height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
</style>
