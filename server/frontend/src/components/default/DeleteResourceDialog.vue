<template>
  <Dialog
    :visible="visible"
    modal
    :header="header"
    :style="{ width }"
    :draggable="false"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="dialog-content">
      <div class="dialog-icon">
        <i class="pi pi-exclamation-triangle"></i>
      </div>
      <h3><slot name="title">Delete "{{ subject }}"?</slot></h3>
      <slot></slot>
    </div>

    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        text
        @click="emit('update:visible', false)"
      />
      <Button
        :label="confirmLabel"
        severity="danger"
        icon="pi pi-trash"
        :loading="loading"
        @click="emit('confirm')"
      />
    </template>
  </Dialog>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, required: true },
  header: { type: String, required: true },
  subject: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Delete' },
  loading: { type: Boolean, default: false },
  width: { type: String, default: '480px' }
})

const emit = defineEmits(['update:visible', 'confirm'])
</script>

<style scoped>
.dialog-content {
  padding: 1rem;
  text-align: center;
}

.dialog-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--danger-subtle);
  border-radius: 50%;
}

.dialog-icon i {
  font-size: 2rem;
  color: var(--danger);
}

.dialog-content h3 {
  margin: 0 0 1rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
}

:slotted(p) {
  margin: 0 0 1rem;
  color: var(--color-text-mute);
  line-height: 1.6;
}

.dialog-content :deep(.p-message) {
  width: 100%;
  margin-top: 1.25rem;
  text-align: left;
}

.dialog-content :deep(.p-message-content) {
  min-height: 3rem;
  align-items: center;
}

.dialog-content :deep(.p-message-text) {
  display: flex;
  align-items: center;
  min-height: 1.5rem;
  line-height: 1.45;
}
</style>
