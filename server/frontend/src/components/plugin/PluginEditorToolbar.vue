<template>
  <div class="editor-topbar">
    <div class="topbar-left">
      <Button
        icon="pi pi-arrow-left"
        text
        rounded
        @click="$emit('back')"
        v-tooltip.bottom="'Back to Plugins'"
      />
      <div class="plugin-title">
        <Icon icon="mdi:firefox" width="28px"/>
        <h2>{{ pluginName || 'Loading...' }}</h2>
      </div>
    </div>

    <div class="topbar-actions">
      <Button
        label="Export"
        icon="pi pi-download"
        severity="secondary"
        outlined
        @click="$emit('export')"
        v-tooltip.bottom="'Export as ZIP'"
      />
      <Button
        label="Save"
        icon="pi pi-save"
        :loading="saving"
        :disabled="saveDisabled"
        @click="$emit('save')"
      />
      <Button
        icon="pi pi-trash"
        severity="danger"
        outlined
        @click="$emit('delete')"
        v-tooltip.bottom="'Delete Plugin'"
      />
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

defineProps({
  pluginName: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false }
})

defineEmits(['back', 'export', 'save', 'delete'])
</script>

<style scoped>
.editor-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background-color: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.plugin-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.plugin-title i {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.plugin-title h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-heading);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

@media (max-width: 768px) {
  .plugin-title h2 {
    display: none;
  }

  .topbar-actions {
    gap: 0.5rem;
  }
}
</style>
