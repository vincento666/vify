<template>
  <a-modal
    v-model:open="visible"
    :title="title"
    :width="width"
    :mask-closable="false"
    destroy-on-close
    @after-close="onClosed"
  >
    <a-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-col="{ style: { width: labelWidth } }"
      @submit.prevent
    >
      <slot :form="formData" :mode="mode" />
    </a-form>

    <template #footer>
      <a-button @click="visible = false">取消</a-button>
      <a-button type="primary" :loading="submitting" @click="onSubmit">
        {{ mode === 'edit' ? '保存' : '确认' }}
      </a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'

type FormRules = Record<string, unknown>
type FormInstance = {
  validate: () => Promise<unknown>
  resetFields: () => void
}

interface Props {
  title: string
  width?: string
  labelWidth?: string
  rules?: FormRules
}

withDefaults(defineProps<Props>(), {
  width: '32.5rem',
  labelWidth: '5.625rem',
  rules: () => ({}),
})

const emit = defineEmits<{
  submit: [data: Record<string, unknown>, mode: 'add' | 'edit']
}>()

const visible = ref(false)
const submitting = ref(false)
const mode = ref<'add' | 'edit'>('add')
const formData = ref<Record<string, unknown>>({})
const formRef = ref<FormInstance>()

const open = (data?: Record<string, unknown>) => {
  mode.value = data ? 'edit' : 'add'
  formData.value = data ? { ...data } : {}
  visible.value = true
}

const onSubmit = async () => {
  await formRef.value?.validate()
  submitting.value = true
  try {
    emit('submit', { ...formData.value }, mode.value)
  } finally {
    submitting.value = false
  }
}

const onClosed = () => {
  formRef.value?.resetFields()
  formData.value = {}
}

const close = () => { visible.value = false }

defineExpose({ open, close, submitting })
</script>
