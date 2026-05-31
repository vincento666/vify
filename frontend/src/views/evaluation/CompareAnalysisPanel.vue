<template>
  <section class="compare-panel">
    <div class="compare-toolbar">
      <label>
        <span>Baseline</span>
        <select v-model.number="baseRunId" data-testid="compare-base-run">
          <option :value="0">选择基线 Run</option>
          <option v-for="run in runs" :key="run.id" :value="run.id">
            {{ runOptionLabel(run) }}
          </option>
        </select>
      </label>
      <label>
        <span>Candidate</span>
        <select v-model.number="candidateRunId" data-testid="compare-candidate-run">
          <option :value="0">选择候选 Run</option>
          <option v-for="run in runs" :key="run.id" :value="run.id">
            {{ runOptionLabel(run) }}
          </option>
        </select>
      </label>
      <el-button
        type="primary"
        data-testid="run-compare"
        :loading="loading"
        @click="runCompare"
      >
        对比
      </el-button>
    </div>

    <div v-if="!compareResult" class="empty-panel compact">
      <h3>选择两次运行进行对比</h3>
      <p>对比会标出新增失败、恢复成功和持续失败的用例。</p>
    </div>

    <template v-else>
      <div class="metric-strip">
        <div>
          <span>Score Delta</span>
          <strong :class="deltaClass(compareResult.scoreDelta)">{{ formatDelta(compareResult.scoreDelta) }}</strong>
          <small>{{ percent(compareResult.baseScore) }} -> {{ percent(compareResult.candidateScore) }}</small>
        </div>
        <div>
          <span>Pass-rate Delta</span>
          <strong :class="deltaClass(compareResult.passRateDelta)">{{ formatDelta(compareResult.passRateDelta) }}</strong>
          <small>{{ percent(compareResult.basePassRate) }} -> {{ percent(compareResult.candidatePassRate) }}</small>
        </div>
        <div>
          <span>Recovered</span>
          <strong>{{ compareResult.recoveredCases.length }}</strong>
          <small>from failed to passed</small>
        </div>
      </div>

      <div class="change-columns">
        <section>
          <h4>{{ summarizeCaseChangeCount('Newly Failed', compareResult.newlyFailedCases.length) }}</h4>
          <ul>
            <li v-for="item in compareResult.newlyFailedCases" :key="`failed-${item.evalCaseId}`">
              <strong>#{{ item.evalCaseId }}</strong>
              <span>{{ item.input }}</span>
            </li>
          </ul>
        </section>
        <section>
          <h4>{{ summarizeCaseChangeCount('Recovered', compareResult.recoveredCases.length) }}</h4>
          <ul>
            <li v-for="item in compareResult.recoveredCases" :key="`recovered-${item.evalCaseId}`">
              <strong>#{{ item.evalCaseId }}</strong>
              <span>{{ item.input }}</span>
            </li>
          </ul>
        </section>
        <section>
          <h4>{{ summarizeCaseChangeCount('Unchanged Failures', compareResult.unchangedFailures.length) }}</h4>
          <ul>
            <li v-for="item in compareResult.unchangedFailures" :key="`unchanged-${item.evalCaseId}`">
              <strong>#{{ item.evalCaseId }}</strong>
              <span>{{ item.input }}</span>
            </li>
          </ul>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  compareEvaluationRuns,
  listEvaluationRuns,
  type EvaluationRun,
  type EvaluationRunCompare,
} from '@/api/evaluation'
import { formatDelta, summarizeCaseChangeCount } from './compareViewModel'

const runs = ref<EvaluationRun[]>([])
const baseRunId = ref(0)
const candidateRunId = ref(0)
const compareResult = ref<EvaluationRunCompare | null>(null)
const loading = ref(false)

onMounted(loadRuns)

async function loadRuns() {
  const page = await listEvaluationRuns({ page: 1, pageSize: 50, status: 'COMPLETED' })
  runs.value = page.list
  candidateRunId.value = runs.value[0]?.id || 0
  baseRunId.value = runs.value[1]?.id || 0
}

async function runCompare() {
  if (!baseRunId.value || !candidateRunId.value || baseRunId.value === candidateRunId.value) {
    ElMessage.error('请选择两个不同的运行记录')
    return
  }
  loading.value = true
  try {
    compareResult.value = await compareEvaluationRuns({
      baseRunId: baseRunId.value,
      candidateRunId: candidateRunId.value,
    })
  } finally {
    loading.value = false
  }
}

function runOptionLabel(run: EvaluationRun) {
  return `Run #${run.id} · ${percent(run.aggregateScore)} · ${run.failedCases} failed`
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function deltaClass(value: number) {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return ''
}
</script>

<style scoped>
.compare-panel {
  padding-top: 2px;
}

.compare-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr) auto;
  gap: 10px;
  align-items: end;
  margin-bottom: 14px;
}

.compare-toolbar label {
  display: grid;
  gap: 6px;
}

.compare-toolbar span,
.metric-strip span,
.metric-strip small,
.change-columns span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.compare-toolbar select {
  height: 34px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 0 10px;
  color: var(--el-text-color-primary);
  background: #fff;
}

.compact {
  min-height: 220px;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-strip > div,
.change-columns section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: #fff;
}

.metric-strip > div {
  display: grid;
  gap: 6px;
  padding: 14px;
}

.metric-strip strong {
  color: var(--el-text-color-primary);
  font-size: 22px;
}

.metric-strip strong.positive {
  color: var(--el-color-success);
}

.metric-strip strong.negative {
  color: var(--el-color-danger);
}

.change-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.change-columns section {
  min-height: 180px;
  padding: 14px;
}

.change-columns h4 {
  margin: 0 0 12px;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.change-columns ul {
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.change-columns li {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
