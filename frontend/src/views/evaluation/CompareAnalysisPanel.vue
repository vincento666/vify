<template>
  <section class="compare-panel">
    <div class="compare-toolbar">
      <label>
        <span>基线运行</span>
        <select v-model.number="baseRunId" data-testid="compare-base-run">
          <option :value="0">选择基线 Run</option>
          <option v-for="run in runs" :key="run.id" :value="run.id">
            {{ runOptionLabel(run) }}
          </option>
        </select>
      </label>
      <label>
        <span>候选运行</span>
        <select v-model.number="candidateRunId" data-testid="compare-candidate-run">
          <option :value="0">选择候选 Run</option>
          <option v-for="run in candidateRunOptions" :key="run.id" :value="run.id">
            {{ runOptionLabel(run) }}
          </option>
        </select>
      </label>
      <a-button
        type="primary"
        data-testid="run-compare"
        :disabled="!canCompareSelected"
        :loading="loading"
        @click="runCompare"
      >
        对比
      </a-button>
    </div>

    <div v-if="!compareResult" class="empty-panel compact">
      <h3>{{ emptyTitle }}</h3>
      <p>{{ emptyDescription }}</p>
    </div>

    <template v-else>
      <div class="metric-strip">
        <div>
          <span>分数变化</span>
          <strong :class="deltaClass(compareResult.scoreDelta)">{{ formatDelta(compareResult.scoreDelta) }}</strong>
          <small>{{ percent(compareResult.baseScore) }} -> {{ percent(compareResult.candidateScore) }}</small>
        </div>
        <div>
          <span>通过率变化</span>
          <strong :class="deltaClass(compareResult.passRateDelta)">{{ formatDelta(compareResult.passRateDelta) }}</strong>
          <small>{{ percent(compareResult.basePassRate) }} -> {{ percent(compareResult.candidatePassRate) }}</small>
        </div>
        <div>
          <span>恢复通过</span>
          <strong>{{ compareResult.recoveredCases.length }}</strong>
          <small>从失败转为通过</small>
        </div>
      </div>

      <div class="change-columns">
        <section>
          <h4>{{ summarizeCaseChangeCount('新增失败', compareResult.newlyFailedCases.length) }}</h4>
          <ul>
            <li v-for="item in compareResult.newlyFailedCases" :key="`failed-${item.evalCaseId}`">
              <strong>#{{ item.evalCaseId }}</strong>
              <span>{{ item.input }}</span>
            </li>
          </ul>
        </section>
        <section>
          <h4>{{ summarizeCaseChangeCount('恢复通过', compareResult.recoveredCases.length) }}</h4>
          <ul>
            <li v-for="item in compareResult.recoveredCases" :key="`recovered-${item.evalCaseId}`">
              <strong>#{{ item.evalCaseId }}</strong>
              <span>{{ item.input }}</span>
            </li>
          </ul>
        </section>
        <section>
          <h4>{{ summarizeCaseChangeCount('持续失败', compareResult.unchangedFailures.length) }}</h4>
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
import { computed, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'

import {
  compareEvaluationRuns,
  listEvaluationRuns,
  type EvaluationRun,
  type EvaluationRunCompare,
} from '@/api/evaluation'
import {
  candidateRunsForBase,
  findDefaultRunPair,
  formatDelta,
  isComparableRunPair,
  runOptionLabel,
  summarizeCaseChangeCount,
} from './compareViewModel'

const runs = ref<EvaluationRun[]>([])
const baseRunId = ref(0)
const candidateRunId = ref(0)
const compareResult = ref<EvaluationRunCompare | null>(null)
const loading = ref(false)
const candidateRunOptions = computed(() => candidateRunsForBase(runs.value, baseRunId.value))
const canCompareSelected = computed(() => isComparableRunPair(runs.value, baseRunId.value, candidateRunId.value))
const emptyTitle = computed(() => {
  if (runs.value.length < 2) return '至少需要两次完成运行'
  if (!candidateRunOptions.value.length) return '当前基线没有可比候选'
  return '选择同一实验的两次运行进行对比'
})
const emptyDescription = computed(() => {
  if (runs.value.length < 2) return '先运行同一个实验两次，才能观察目标变更带来的质量变化。'
  if (!candidateRunOptions.value.length) return '请选择另一个有多次运行的基线，或先重新运行该实验。'
  return '对比会标出新增失败、恢复成功和持续失败的用例。'
})

onMounted(loadRuns)

watch(baseRunId, () => {
  if (!candidateRunOptions.value.some((run) => run.id === candidateRunId.value)) {
    candidateRunId.value = candidateRunOptions.value[0]?.id || 0
  }
  compareResult.value = null
})

watch(candidateRunId, () => {
  compareResult.value = null
})

async function loadRuns() {
  const page = await listEvaluationRuns({ page: 1, pageSize: 50, status: 'COMPLETED' })
  runs.value = page.list
  const defaultPair = findDefaultRunPair(runs.value)
  baseRunId.value = defaultPair.baseRunId
  candidateRunId.value = defaultPair.candidateRunId
}

async function runCompare() {
  if (!canCompareSelected.value) {
    message.error('请选择同一实验的两次不同运行')
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
  padding-top: 0.125rem;
}

.compare-toolbar {
  display: grid;
  grid-template-columns: minmax(13.75rem, 1fr) minmax(13.75rem, 1fr) auto;
  gap: 0.625rem;
  align-items: end;
  margin-bottom: 0.875rem;
}

.compare-toolbar label {
  display: grid;
  gap: 0.375rem;
}

.compare-toolbar span,
.metric-strip span,
.metric-strip small,
.change-columns span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.compare-toolbar select {
  height: 2.125rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0 0.625rem;
  color: var(--color-text-primary);
  background: #fff;
}

.compact {
  min-height: 13.75rem;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.metric-strip > div,
.change-columns section {
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: #fff;
}

.metric-strip > div {
  display: grid;
  gap: 0.375rem;
  padding: 0.875rem;
}

.metric-strip strong {
  color: var(--color-text-primary);
  font-size: 1.375rem;
}

.metric-strip strong.positive {
  color: #16a34a;
}

.metric-strip strong.negative {
  color: #dc2626;
}

.change-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.change-columns section {
  min-height: 11.25rem;
  padding: 0.875rem;
}

.change-columns h4 {
  margin: 0 0 var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.change-columns ul {
  display: grid;
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.change-columns li {
  display: grid;
  grid-template-columns: 3.375rem minmax(0, 1fr);
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2) 0;
  border-top: 0.0625rem solid var(--color-border-default);
}
</style>
