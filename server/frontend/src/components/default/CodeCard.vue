<template>
  <div class="code-card">
    <div class="code-card-header">
      <div class="header-left">
        <Icon v-if="iconIconify" :icon="iconIconify" width="20px" />
        <i v-else :class="icon"></i>
        <span>{{ title }}</span>
        <Badge v-if="required && !modelValue" value="Required" severity="danger" />
      </div>
      <div class="header-right">
        <span v-if="showStats" class="stat-item">
          <i class="pi pi-file"></i>
          {{ fileSize }}
        </span>
        <span v-if="showStats" class="stat-item">
          <i class="pi pi-list"></i>
          {{ lineCount }} lines
        </span>

        <!-- Actions predefinite -->
        <Button
          v-if="showFormat"
          icon="pi pi-align-justify"
          severity="secondary"
          text
          rounded
          size="small"
          @click="formatCode"
          v-tooltip.top="'Format code'"
        />
        <Button
          icon="pi pi-copy"
          severity="secondary"
          text
          rounded
          size="small"
          @click="copyToClipboard"
          v-tooltip.top="'Copy to clipboard'"
        />
      </div>
    </div>

    <div class="code-card-body">
      <CodeEditor
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        :language="language"
        :theme="theme"
        :height="height"
        :read-only="readOnly"
      />
    </div>

    <small v-if="error" class="p-error code-error">{{ error }}</small>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import CodeEditor from '@/components/default/CodeEditor.vue'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import { Icon } from '@iconify/vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: 'Code'
  },
  icon: {
    type: String,
    default: 'pi pi-code'
  },
  iconIconify: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'html'
  },
  theme: {
    type: String,
    default: 'bitm-dark'
  },
  height: {
    type: [String, Number],
    default: 400
  },
  readOnly: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  showStats: {
    type: Boolean,
    default: true
  },
  showFormat: {
    type: Boolean,
    default: true
  },
  error: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const toast = useToast()

// Computed
const fileSize = computed(() => {
  const blob = new Blob([props.modelValue || ''])
  const bytes = blob.size
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

const lineCount = computed(() => {
  return (props.modelValue || '').split('\n').length
})

// Methods
const formatCode = () => {
  try {
    let formatted = props.modelValue.trim()

    // Basic HTML formatting
    if (props.language === 'html') {
      // Simple indentation fix
      formatted = formatted.replace(/>\s*</g, '>\n<')
    }

    emit('update:modelValue', formatted)

    toast.add({
      severity: 'success',
      summary: 'Formatted',
      detail: 'Code formatted successfully',
      life: 2000
    })
  } catch (_error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to format code',
      life: 3000
    })
  }
}

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.modelValue || '')
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: `${props.title} copied to clipboard`,
      life: 2000
    })
  } catch (_error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy to clipboard',
      life: 3000
    })
  }
}
</script>

<style scoped>
.code-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  min-height: 0;
}

.code-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  flex: 0 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--code-text);
}

.header-left i {
  color: var(--primary-color);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-right :deep(.p-button) {
  color: var(--code-muted);
}

.header-right :deep(.p-button:hover) {
  background: var(--code-raised);
  color: var(--code-text);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.813rem;
  color: var(--code-muted);
}

.stat-item i {
  font-size: 0.75rem;
}

.code-card-body {
  flex: 1 1 auto;
  min-height: 0;
  background: var(--code-canvas);
  border: 1px solid var(--code-border);
  border-top: none;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  overflow: hidden;
}

.code-error {
  display: block;
  margin-top: 0.5rem;
  color: var(--red-500);
  font-size: 0.813rem;
}

/* Responsive */
@media (max-width: 768px) {
  .code-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .stat-item {
    font-size: 0.75rem;
  }
}
</style>
