<template>
  <div class="hify-table-wrap">
    <a-table
      class="hify-table"
      :columns="antColumns"
      :data-source="rows"
      :loading="loading"
      :pagination="false"
      :custom-row="customRow"
      :row-key="rowKey"
      size="middle"
    >
      <template #bodyCell="{ column, record, index }">
        <slot
          v-if="column.customSlot"
          :name="column.customSlot"
          :row="record"
          :column="column"
          :index="index"
          :$index="index"
        />
        <template v-else>
          {{ displayCellValue(record, column.dataIndex) }}
        </template>
      </template>
    </a-table>

    <div v-if="showPagination && total > 0" class="hify-table-pagination">
      <a-pagination
        :current="page"
        :page-size="pageSize"
        :total="total"
        :page-size-options="['10', '20', '50']"
        :show-total="showTotal"
        show-size-changer
        @change="onPageChange"
        @showSizeChange="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { normalizeElementTableSize } from './hifyTableSizing'

export interface TableColumn {
  label: string
  prop?: string
  slot?: string
  width?: number | string
  minWidth?: number | string
  ellipsis?: boolean
  hideOnNarrow?: boolean
}

interface PageResult {
  list: Record<string, unknown>[]
  total: number
}

interface Props {
  columns: TableColumn[]
  api: (params: { page: number; pageSize: number }) => Promise<PageResult>
  showPagination?: boolean
  rowStyle?: Record<string, string>
  rowKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  showPagination: true,
  rowStyle: () => ({}),
  rowKey: 'id',
})

const rows = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const isNarrow = ref(window.innerWidth < 1200)

const onResize = () => { isNarrow.value = window.innerWidth < 1200 }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const visibleColumns = computed(() =>
  props.columns.filter(col => !(isNarrow.value && col.hideOnNarrow))
)

interface AntTableColumn {
  title: string
  dataIndex?: string
  key: string
  width?: number | string
  minWidth?: number | string
  ellipsis?: boolean
  customSlot?: string
}

const antColumns = computed<AntTableColumn[]>(() =>
  visibleColumns.value.map((col) => ({
    title: col.label,
    dataIndex: col.prop,
    key: col.slot ?? col.prop ?? col.label,
    width: normalizeElementTableSize(col.width),
    minWidth: normalizeElementTableSize(col.minWidth),
    ellipsis: col.ellipsis ?? true,
    customSlot: col.slot,
  }))
)

const rowKey = (row: Record<string, unknown>) => {
  const value = row[props.rowKey]
  return typeof value === 'string' || typeof value === 'number' ? value : JSON.stringify(row)
}

const customRow = () => ({
  style: props.rowStyle,
})

const displayCellValue = (record: Record<string, unknown>, dataIndex: unknown) => {
  if (typeof dataIndex !== 'string') return ''
  const value = record[dataIndex]
  return value == null ? '' : String(value)
}

const load = async () => {
  loading.value = true
  try {
    const res = await props.api({ page: page.value, pageSize: pageSize.value })
    rows.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const onPageChange = (nextPage: number, nextPageSize?: number) => {
  page.value = nextPage
  if (nextPageSize) pageSize.value = nextPageSize
  load()
}
const onSizeChange = (_current: number, nextPageSize: number) => {
  pageSize.value = nextPageSize
  page.value = 1
  load()
}
const showTotal = (nextTotal: number) => `共 ${nextTotal} 条`

const refresh = () => { page.value = 1; load() }

onMounted(load)
defineExpose({ refresh })
</script>

<style scoped>
.hify-table-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.hify-table {
  width: 100%;
}

.hify-table :deep(.ant-empty-image) {
  height: 5rem;
}

.hify-table-pagination {
  display: flex;
  justify-content: flex-end;
}
</style>
