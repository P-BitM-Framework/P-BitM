<template>
  <div class="sidebar-section">
    <div class="section-header">
      <h3>
        <i class="pi pi-cog"></i>
        Settings
      </h3>
    </div>

    <div class="settings-form">
      <div class="field">
        <label>Plugin Name</label>
        <InputText
          v-model="plugin.name"
          @input="$emit('edited')"
          placeholder="Plugin name"
        />
      </div>

      <div class="field">
        <label>Description</label>
        <Textarea
          v-model="plugin.description"
          @input="$emit('edited')"
          rows="3"
          placeholder="Plugin description"
        />
      </div>

      <div class="plugin-info">
        <div class="info-row">
          <span class="info-label">Created:</span>
          <span class="info-value">{{ formatDateLocal(plugin.created_at) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Files:</span>
          <span class="info-value">{{ fileCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDateLocal } from '@/utils/utils'

defineProps({
  plugin: { type: Object, required: true },
  fileCount: { type: Number, default: 0 }
})

defineEmits(['edited'])
</script>

<style scoped>
.sidebar-section {
  margin-bottom: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-heading);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-header h3 i {
  font-size: 0.875rem;
  color: var(--color-text-mute);
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.813rem;
  color: var(--color-heading);
}

.plugin-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background-color: var(--color-background-mute);
  border-radius: 6px;
  margin-top: 0.5rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
}

.info-label {
  color: var(--color-text-mute);
}

.info-value {
  color: var(--color-heading);
  font-weight: 500;
}
</style>
