<template>
  <section class="observe-redirect" data-testid="observe-redirect">
    <span>正在打开运行详情...</span>
  </section>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getObserveRun } from '@/api/observe'
import { buildObserveComposerRedirect, normalizeObserveRedirectRunId } from './observeRedirect'

const route = useRoute()
const router = useRouter()

async function redirectToComposer() {
  const runId = normalizeObserveRedirectRunId(route.query.runId)
  if (!runId) {
    await router.replace('/workflows')
    return
  }

  try {
    const detail = await getObserveRun(runId)
    await router.replace(buildObserveComposerRedirect({ runId, detail }))
  } catch {
    await router.replace('/workflows')
  }
}

onMounted(redirectToComposer)
watch(() => route.fullPath, redirectToComposer)
</script>

<style scoped>
.observe-redirect {
  min-height: 100vh;
  display: grid;
  place-items: center;
  color: #6b7280;
  background: #f8fafc;
}
</style>
