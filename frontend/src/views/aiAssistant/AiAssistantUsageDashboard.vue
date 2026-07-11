<template>
  <section class="usage-page" data-testid="ai-assistant-usage-dashboard">
    <header class="usage-header">
      <div>
        <router-link class="usage-back" to="/ai-assistant">← 返回 AI 助手</router-link>
        <h1>Token 用量</h1>
        <p>当前工作区的模型 Token 与成本统计</p>
      </div>
      <div class="metric-toggle" data-testid="ai-assistant-usage-metric-toggle" aria-label="统计指标">
        <button :class="{ active: metric === 'tokens' }" :aria-pressed="metric === 'tokens'" type="button" @click="metric = 'tokens'">Token</button>
        <button :class="{ active: metric === 'cost' }" :aria-pressed="metric === 'cost'" type="button" @click="metric = 'cost'">Cost</button>
      </div>
    </header>

    <div v-if="loading" class="usage-state" data-testid="ai-assistant-usage-loading" role="status" aria-live="polite">
      <LoadingOutlined spin /> 正在加载用量数据…
    </div>

    <div v-else-if="error" class="usage-state usage-state--error" data-testid="ai-assistant-usage-error" role="alert">
      <ExclamationCircleOutlined />
      <span>{{ error }}</span>
      <button type="button" @click="loadDashboard">重试</button>
    </div>

    <template v-else>
      <section class="summary-grid" data-testid="ai-assistant-usage-summary">
        <article v-for="card in summaryCards" :key="card.label" class="summary-card">
          <span>{{ card.label }}</span>
          <strong>{{ formatTokenCount(card.value.totalTokens) }} tokens</strong>
          <div class="summary-card__meta">
            <span>{{ formatCostState(card.value) }}</span>
            <span>{{ card.value.sessionCount }} 次会话</span>
          </div>
        </article>
      </section>

      <div
        v-if="hasUnknownCost"
        class="unknown-banner"
        data-testid="ai-assistant-usage-unknown-cost"
      >
        <InfoCircleOutlined />
        <span>部分模型价格未知；Cost 仅累计已知费用，不把未知费用显示为 0。</span>
      </div>

      <div v-if="isEmpty" class="usage-state" data-testid="ai-assistant-usage-empty">
        <InboxOutlined /> 当前范围暂无 Token 用量
      </div>

      <template v-else>
        <section class="usage-panel heatmap-panel" data-testid="ai-assistant-usage-heatmap">
          <div class="panel-heading">
            <div>
              <h2>每日用量</h2>
              <p>近 12 个月 · {{ metric === 'tokens' ? 'Token' : 'Cost' }} 强度</p>
            </div>
            <div class="heatmap-legend" aria-label="热力图图例">
              <span>少</span>
              <i v-for="level in [0, 1, 2, 3, 4, 5]" :key="level" :class="`level-${level}`" />
              <span>多</span>
            </div>
          </div>
          <div class="heatmap-scroll">
            <div class="heatmap-weekdays" aria-hidden="true">
              <span>一</span><span></span><span>三</span><span></span><span>五</span><span></span><span>日</span>
            </div>
            <div class="heatmap-calendar">
              <div class="heatmap-months" :style="{ gridTemplateColumns: `repeat(${heatmapWeekColumns}, 0.92rem)` }">
                <span
                  v-for="month in heatmapMonths"
                  :key="`${month.label}-${month.column}`"
                  :style="{ gridColumn: `${month.column} / span 4` }"
                >{{ month.label }}</span>
              </div>
              <div class="heatmap-grid">
              <i v-for="padding in heatmapPadding" :key="`padding-${padding}`" class="heatmap-cell level-0" />
              <i
                v-for="cell in heatmapCells"
                :key="cell.date"
                class="heatmap-cell"
                :class="[`level-${cell.intensity}`, { unknown: cell.unknownCost }]"
                role="img"
                :data-date="cell.date"
                :title="heatmapTitle(cell)"
                :aria-label="heatmapTitle(cell)"
              />
              </div>
            </div>
          </div>
        </section>

        <section class="detail-controls" data-testid="ai-assistant-usage-range">
          <div>
            <h2>用量详情</h2>
            <p>默认查看最近 30 天</p>
          </div>
          <label>从 <input v-model="detailFrom" type="date" :max="detailTo" /></label>
          <label>至 <input v-model="detailTo" type="date" :min="detailFrom" /></label>
          <button type="button" :disabled="detailLoading" @click="loadDetailRange">应用</button>
        </section>

        <div v-if="detailError" class="detail-error" data-testid="ai-assistant-usage-detail-error" role="alert">
          <span>{{ detailError }}</span>
          <button type="button" @click="loadDetailRange">重试详情</button>
        </div>

        <div v-if="detailLoading" class="inline-loading"><LoadingOutlined spin /> 更新详情…</div>

        <section class="usage-layout">
          <article class="usage-panel" data-testid="ai-assistant-usage-sessions">
            <div class="panel-heading">
              <div><h2>会话排行</h2><p>按 Token 总量排序</p></div>
              <span>{{ sessionTotal }} 个会话</span>
            </div>
            <div class="session-list">
              <button
                v-for="item in sessions"
                :key="item.sessionId"
                class="session-row"
                :class="{ active: selectedSessionId === item.sessionId }"
                type="button"
                @click="loadSessionDetail(item.sessionId)"
              >
                <span><strong>{{ item.title || `会话 ${item.sessionId}` }}</strong><small>{{ item.callCount }} 次调用</small></span>
                <span><strong>{{ formatTokenCount(item.totalTokens) }}</strong><small>{{ formatCostState(item) }}</small></span>
              </button>
            </div>
            <div v-if="sessionTotal > sessionPageSize" class="pagination" data-testid="ai-assistant-usage-session-pagination">
              <button type="button" :disabled="sessionOffset === 0" @click="changeSessionPage(-1)">上一页</button>
              <span>{{ sessionOffset + 1 }}–{{ Math.min(sessionOffset + sessions.length, sessionTotal) }} / {{ sessionTotal }}</span>
              <button type="button" :disabled="sessionOffset + sessionPageSize >= sessionTotal" @click="changeSessionPage(1)">下一页</button>
            </div>
          </article>

          <article class="usage-panel" data-testid="ai-assistant-usage-token-types">
            <div class="panel-heading"><div><h2>Token 构成</h2><p>Provider 可用维度</p></div></div>
            <div class="composition-list">
              <div v-for="item in tokenComposition" :key="item.label" class="composition-row">
                <div><span>{{ item.label }}</span><strong>{{ formatTokenCount(item.value) }}</strong></div>
                <div class="bar-track"><i :style="{ width: tokenTypeWidth(item.value) }" /></div>
              </div>
            </div>
          </article>
        </section>

        <section class="distribution-grid">
          <article class="usage-panel" data-testid="ai-assistant-usage-providers">
            <div class="panel-heading"><div><h2>Provider 分布</h2><p>{{ metricLabel }} 占比</p></div></div>
            <div v-for="item in dimensions?.providers || []" :key="item.name" class="distribution-row">
              <div><strong>{{ item.name }}</strong><span>{{ metricValue(item) }}</span></div>
              <div class="bar-track"><i :style="{ width: distributionWidth(item, dimensions?.providers || []) }" /></div>
            </div>
          </article>

          <article class="usage-panel" data-testid="ai-assistant-usage-models">
            <div class="panel-heading"><div><h2>模型分布</h2><p>{{ metricLabel }} 占比</p></div></div>
            <div v-for="item in dimensions?.models || []" :key="item.name" class="distribution-row">
              <div><strong>{{ item.name }}</strong><span>{{ metricValue(item) }}</span></div>
              <div class="bar-track"><i :style="{ width: distributionWidth(item, dimensions?.models || []) }" /></div>
            </div>
          </article>
        </section>

        <section v-if="sessionDetail" class="usage-panel session-detail" data-testid="ai-assistant-usage-session-detail">
          <div class="panel-heading">
            <div>
              <h2>{{ sessionDetail.title }}</h2>
              <p>{{ sessionDetail.callCount }} 次模型调用 · {{ formatTokenCount(sessionDetail.totalTokens) }} tokens</p>
            </div>
            <button type="button" @click="closeSessionDetail">关闭</button>
          </div>
          <div class="call-table-wrap">
            <table>
              <thead><tr><th>时间</th><th>类型</th><th>Provider / 模型</th><th>Token</th><th>Cost</th></tr></thead>
              <tbody>
                <tr v-for="call in sessionDetail.calls" :key="call.id">
                  <td>{{ formatDateTime(call.startedAt) }}</td>
                  <td>{{ call.callKind }}</td>
                  <td>{{ call.provider }} / {{ call.model }}</td>
                  <td>{{ formatOptionalTokenCount(call.totalTokens) }}</td>
                  <td>{{ formatCallCost(call.costUsd) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="sessionDetail.callCount > detailPageSize" class="pagination" data-testid="ai-assistant-usage-call-pagination">
            <button type="button" :disabled="detailOffset === 0" @click="changeDetailPage(-1)">上一页</button>
            <span>{{ detailOffset + 1 }}–{{ Math.min(detailOffset + sessionDetail.calls.length, sessionDetail.callCount) }} / {{ sessionDetail.callCount }}</span>
            <button type="button" :disabled="detailOffset + detailPageSize >= sessionDetail.callCount" @click="changeDetailPage(1)">下一页</button>
          </div>
        </section>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import {
  ExclamationCircleOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons-vue'
import { computed, onMounted, ref } from 'vue'

import {
  getAiAssistantUsageDaily,
  getAiAssistantUsageDimensions,
  getAiAssistantUsageSession,
  getAiAssistantUsageSessions,
  getAiAssistantUsageSummary,
  type AiAssistantUsageDaily,
  type AiAssistantUsageDimensions,
  type AiAssistantUsageNamedTotal,
  type AiAssistantUsageSession,
  type AiAssistantUsageSessionDetail,
  type AiAssistantUsageSummary,
} from '@/api/aiAssistant'
import {
  buildUsageHeatmap,
  formatCallCost,
  formatCostState,
  formatOptionalTokenCount,
  formatTokenCount,
  parseUsageUtcDateTime,
  usageDateRange,
  type UsageHeatmapCell,
  type UsageMetric,
} from './aiAssistantUsageViewModel'

const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
const initialRange = usageDateRange()
const metric = ref<UsageMetric>('tokens')
const detailFrom = ref(initialRange.detailFrom)
const detailTo = ref(initialRange.to)
const appliedFrom = ref(initialRange.detailFrom)
const appliedTo = ref(initialRange.to)
const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
const detailError = ref('')
const summary = ref<AiAssistantUsageSummary | null>(null)
const daily = ref<AiAssistantUsageDaily[]>([])
const sessions = ref<AiAssistantUsageSession[]>([])
const sessionTotal = ref(0)
const sessionPageSize = 50
const sessionOffset = ref(0)
const detailPageSize = 100
const detailOffset = ref(0)
const dimensions = ref<AiAssistantUsageDimensions | null>(null)
const selectedSessionId = ref<number | null>(null)
const sessionDetail = ref<AiAssistantUsageSessionDetail | null>(null)
let sessionDetailRequestSequence = 0

const summaryCards = computed(() => {
  if (!summary.value) return []
  return [
    { label: '今天', value: summary.value.today },
    { label: '昨天', value: summary.value.yesterday },
    { label: '30 天', value: summary.value.rolling30Days },
    { label: '累计', value: summary.value.cumulative },
  ]
})
const heatmapCells = computed(() =>
  buildUsageHeatmap(daily.value, initialRange.heatmapFrom, initialRange.to, metric.value),
)
const heatmapPadding = computed(() => {
  const day = new Date(`${initialRange.heatmapFrom}T12:00:00`).getDay()
  return day === 0 ? 6 : day - 1
})
const heatmapWeekColumns = computed(() => Math.ceil((heatmapPadding.value + heatmapCells.value.length) / 7))
const heatmapMonths = computed(() => {
  const labels: Array<{ label: string; column: number }> = []
  const occupied = new Set<number>()
  heatmapCells.value.forEach((cell, index) => {
    const date = new Date(`${cell.date}T12:00:00`)
    if (index !== 0 && date.getDate() !== 1) return
    const column = Math.floor((heatmapPadding.value + index) / 7) + 1
    if (occupied.has(column)) return
    occupied.add(column)
    labels.push({ label: `${date.getMonth() + 1}月`, column })
  })
  return labels
})
const isEmpty = computed(() => (summary.value?.cumulative.totalTokens || 0) === 0)
const hasUnknownCost = computed(() => (summary.value?.cumulative.unknownCostCount || 0) > 0)
const metricLabel = computed(() => (metric.value === 'tokens' ? 'Token' : 'Cost'))
const tokenComposition = computed(() => {
  const values = dimensions.value?.tokenTypes
  return values
    ? [
        { label: '输入', value: values.input },
        { label: '输出', value: values.output },
        { label: '缓存读取', value: values.cacheRead },
        { label: '缓存写入', value: values.cacheWrite },
        { label: '推理', value: values.reasoning },
      ]
    : []
})

function detailQuery() {
  return { from: appliedFrom.value, to: appliedTo.value, timezone }
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [summaryResult, dailyResult] = await Promise.all([
      getAiAssistantUsageSummary({ timezone }),
      getAiAssistantUsageDaily({ from: initialRange.heatmapFrom, to: initialRange.to, timezone }),
    ])
    summary.value = summaryResult
    daily.value = dailyResult.list
    await loadDetailRange()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '用量数据加载失败'
  } finally {
    loading.value = false
  }
}

async function loadDetailRange() {
  if (detailFrom.value > detailTo.value) {
    detailError.value = '开始日期不能晚于结束日期'
    return
  }
  detailLoading.value = true
  detailError.value = ''
  const nextQuery = { from: detailFrom.value, to: detailTo.value, timezone }
  try {
    const [sessionResult, dimensionResult] = await Promise.all([
      getAiAssistantUsageSessions(nextQuery, { limit: sessionPageSize, offset: 0 }),
      getAiAssistantUsageDimensions(nextQuery),
    ])
    appliedFrom.value = nextQuery.from
    appliedTo.value = nextQuery.to
    sessionOffset.value = 0
    sessions.value = sessionResult.list
    sessionTotal.value = sessionResult.total
    dimensions.value = dimensionResult
    closeSessionDetail()
  } catch (cause) {
    detailError.value = cause instanceof Error ? cause.message : '详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

async function loadSessionDetail(sessionId: number) {
  const requestSequence = ++sessionDetailRequestSequence
  selectedSessionId.value = sessionId
  detailOffset.value = 0
  detailError.value = ''
  sessionDetail.value = null
  try {
    const result = await getAiAssistantUsageSession(
      sessionId,
      detailQuery(),
      { limit: detailPageSize, offset: 0 },
    )
    if (requestSequence === sessionDetailRequestSequence && selectedSessionId.value === sessionId) {
      sessionDetail.value = result
    }
  } catch (cause) {
    if (requestSequence === sessionDetailRequestSequence && selectedSessionId.value === sessionId) {
      detailError.value = cause instanceof Error ? cause.message : '会话详情加载失败'
    }
  }
}

async function changeSessionPage(direction: -1 | 1) {
  const nextOffset = Math.max(0, sessionOffset.value + direction * sessionPageSize)
  detailLoading.value = true
  detailError.value = ''
  try {
    const result = await getAiAssistantUsageSessions(detailQuery(), {
      limit: sessionPageSize,
      offset: nextOffset,
    })
    sessionOffset.value = nextOffset
    sessions.value = result.list
    sessionTotal.value = result.total
    closeSessionDetail()
  } catch (cause) {
    detailError.value = cause instanceof Error ? cause.message : '会话分页加载失败'
  } finally {
    detailLoading.value = false
  }
}

async function changeDetailPage(direction: -1 | 1) {
  if (selectedSessionId.value === null) return
  const sessionId = selectedSessionId.value
  const requestSequence = ++sessionDetailRequestSequence
  const nextOffset = Math.max(0, detailOffset.value + direction * detailPageSize)
  detailError.value = ''
  try {
    const result = await getAiAssistantUsageSession(
      sessionId,
      detailQuery(),
      { limit: detailPageSize, offset: nextOffset },
    )
    if (requestSequence === sessionDetailRequestSequence && selectedSessionId.value === sessionId) {
      sessionDetail.value = result
      detailOffset.value = nextOffset
    }
  } catch (cause) {
    if (requestSequence === sessionDetailRequestSequence && selectedSessionId.value === sessionId) {
      detailError.value = cause instanceof Error ? cause.message : '调用分页加载失败'
    }
  }
}

function closeSessionDetail() {
  sessionDetailRequestSequence += 1
  selectedSessionId.value = null
  sessionDetail.value = null
  detailOffset.value = 0
}

function metricNumber(item: AiAssistantUsageNamedTotal): number {
  return metric.value === 'tokens' ? item.totalTokens : Number(item.costUsd || 0)
}

function distributionWidth(item: AiAssistantUsageNamedTotal, rows: AiAssistantUsageNamedTotal[]): string {
  if (metricNumber(item) <= 0) return '0%'
  const maximum = Math.max(0, ...rows.map(metricNumber))
  return maximum ? `${(metricNumber(item) / maximum) * 100}%` : '0%'
}

function tokenTypeWidth(value: number): string {
  if (value <= 0) return '0%'
  const maximum = Math.max(0, ...tokenComposition.value.map((item) => item.value))
  return maximum ? `${(value / maximum) * 100}%` : '0%'
}

function metricValue(item: AiAssistantUsageNamedTotal): string {
  return metric.value === 'tokens' ? formatTokenCount(item.totalTokens) : formatCostState(item)
}

function heatmapTitle(cell: UsageHeatmapCell): string {
  const value = metric.value === 'tokens'
    ? `${formatTokenCount(cell.totalTokens)} tokens`
    : formatCostState({ costUsd: cell.costUsd, costState: cell.costState, unknownCostCount: cell.unknownCost ? 1 : 0 })
  return `${cell.date} · ${value}`
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(
    parseUsageUtcDateTime(value),
  )
}

onMounted(loadDashboard)
</script>

<style scoped>
.usage-page {
  min-height: 100%;
  padding: 1.5rem;
  color: #172033;
  background: linear-gradient(145deg, #f7f4ef 0%, #f5f7f2 55%, #eef5f2 100%);
}

.usage-header,
.panel-heading,
.detail-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.usage-header { margin-bottom: 1.25rem; }
.usage-header h1 { margin: 0.25rem 0 0; font-size: 1.65rem; }
.usage-header p,
.panel-heading p,
.detail-controls p { margin: 0.2rem 0 0; color: #798094; }
.usage-back { color: #657087; font-size: 0.82rem; }

.metric-toggle {
  display: inline-flex;
  padding: 0.2rem;
  border: 1px solid #d9ded7;
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.85);
}

.metric-toggle button,
.detail-controls button,
.usage-state button,
.panel-heading button {
  border: 0;
  border-radius: 0.45rem;
  padding: 0.5rem 0.8rem;
  color: #566078;
  background: transparent;
  cursor: pointer;
}

.metric-toggle button.active,
.detail-controls button,
.usage-state button {
  color: #fff;
  background: #b9473f;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
}

.summary-card,
.usage-panel,
.detail-controls,
.usage-state,
.unknown-banner {
  border: 1px solid rgba(137, 146, 137, 0.24);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 0.4rem 1.4rem rgba(56, 67, 58, 0.05);
}

.summary-card { padding: 1rem; }
.summary-card > span { color: #747b8d; font-size: 0.78rem; }
.summary-card > strong { display: block; margin: 0.4rem 0; font-size: 1.35rem; }
.summary-card__meta { display: flex; justify-content: space-between; color: #8b5360; font-size: 0.74rem; }

.unknown-banner {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  margin-top: 0.9rem;
  padding: 0.75rem 0.9rem;
  color: #7a5230;
  background: rgba(255, 247, 226, 0.92);
}

.usage-panel { margin-top: 1rem; padding: 1rem; }
.panel-heading h2,
.detail-controls h2 { margin: 0; font-size: 1rem; }
.heatmap-panel { overflow: hidden; }
.heatmap-scroll { display: flex; gap: 0.6rem; margin-top: 1rem; overflow-x: auto; padding-bottom: 0.35rem; }
.heatmap-weekdays { display: grid; grid-template-rows: repeat(7, 0.72rem); gap: 0.2rem; margin-top: 1.2rem; color: #8b918c; font-size: 0.6rem; }
.heatmap-calendar { min-width: max-content; }
.heatmap-months { display: grid; height: 1rem; margin-bottom: 0.2rem; color: #727983; font-size: 0.65rem; line-height: 1rem; }
.heatmap-months span { overflow: visible; white-space: nowrap; }
.heatmap-grid { display: grid; grid-auto-flow: column; grid-template-rows: repeat(7, 0.72rem); gap: 0.2rem; min-width: max-content; }
.heatmap-cell { width: 0.72rem; height: 0.72rem; padding: 0; border: 0; border-radius: 0.16rem; background: #e7e9e4; }
.heatmap-cell.level-1, .heatmap-legend .level-1 { background: #efc5bb; }
.heatmap-cell.level-2, .heatmap-legend .level-2 { background: #e99d8e; }
.heatmap-cell.level-3, .heatmap-legend .level-3 { background: #df7467; }
.heatmap-cell.level-4, .heatmap-legend .level-4 { background: #c94d48; }
.heatmap-cell.level-5, .heatmap-legend .level-5 { background: #9f302f; }
.heatmap-cell.unknown { outline: 1px dashed #9b692b; }
.heatmap-legend { display: flex; align-items: center; gap: 0.22rem; color: #8b918c; font-size: 0.65rem; }
.heatmap-legend i { width: 0.65rem; height: 0.65rem; border-radius: 0.13rem; background: #e7e9e4; }

.detail-controls { margin-top: 1rem; padding: 0.8rem 1rem; }
.detail-controls label { display: flex; align-items: center; gap: 0.4rem; color: #687086; }
.detail-controls input { border: 1px solid #d8ddd7; border-radius: 0.4rem; padding: 0.38rem; background: #fff; }
.detail-controls button:disabled { opacity: 0.55; cursor: wait; }
.inline-loading { padding: 0.7rem; text-align: center; color: #737b8d; }
.detail-error { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-top: 0.7rem; padding: 0.65rem 0.8rem; border: 1px solid #efb3ad; border-radius: 0.55rem; color: #9d302f; background: #fff4f2; }
.detail-error button { border: 0; color: #9d302f; background: transparent; cursor: pointer; }

.usage-layout,
.distribution-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.session-list { display: grid; gap: 0.45rem; margin-top: 0.8rem; }
.session-row { display: flex; justify-content: space-between; gap: 1rem; width: 100%; padding: 0.65rem; border: 1px solid transparent; border-radius: 0.55rem; text-align: left; background: #f6f7f4; cursor: pointer; }
.session-row.active { border-color: #c6534d; background: #fff3f0; }
.session-row span:last-child { text-align: right; }
.session-row strong, .session-row small { display: block; }
.session-row small { margin-top: 0.18rem; color: #858c98; }
.pagination { display: flex; align-items: center; justify-content: flex-end; gap: 0.6rem; margin-top: 0.75rem; color: #737b8d; font-size: 0.72rem; }
.pagination button { border: 1px solid #d8ddd7; border-radius: 0.4rem; padding: 0.35rem 0.55rem; color: #566078; background: #fff; cursor: pointer; }
.pagination button:disabled { opacity: 0.45; cursor: default; }
.composition-list, .distribution-row { margin-top: 0.8rem; }
.composition-row { margin-bottom: 0.7rem; }
.composition-row > div:first-child,
.distribution-row > div:first-child { display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 0.28rem; }
.bar-track { height: 0.42rem; overflow: hidden; border-radius: 1rem; background: #eceee9; }
.bar-track i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #b73e3b, #df826e); }

.session-detail { margin-bottom: 1rem; }
.call-table-wrap { margin-top: 0.8rem; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
th, td { padding: 0.62rem; border-bottom: 1px solid #e7e9e4; text-align: left; white-space: nowrap; }
th { color: #737b8b; font-weight: 600; }

.usage-state { display: flex; justify-content: center; align-items: center; gap: 0.6rem; min-height: 8rem; margin-top: 1rem; padding: 1rem; color: #697187; }
.usage-state--error { color: #9d302f; background: #fff4f2; }

@media (max-width: 70rem) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .usage-layout, .distribution-grid { grid-template-columns: 1fr; }
}

@media (max-width: 44rem) {
  .usage-page { padding: 1rem; }
  .usage-header, .detail-controls { align-items: flex-start; flex-direction: column; }
  .summary-grid { grid-template-columns: 1fr; }
}
</style>
