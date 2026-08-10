<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  confirmLabel: {
    type: String,
    default: 'Confirm'
  },
  confirmIcon: {
    type: String,
    default: 'pi pi-check'
  },
  icon: {
    type: String,
    default: 'pi pi-exclamation-triangle'
  },
  tone: {
    type: String,
    default: 'danger',
    validator: (value) => ['danger', 'warning'].includes(value)
  },
  busy: {
    type: Boolean,
    default: false
  },
  width: {
    type: String,
    default: '440px'
  }
})

defineEmits(['update:visible', 'cancel', 'confirm'])
</script>

<template>
  <Dialog
    :visible="visible"
    :header="title"
    :style="{ width }"
    :closable="!busy"
    :draggable="false"
    modal
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="confirm-dialog-content">
      <div class="confirm-dialog-icon" :class="`confirm-dialog-icon--${tone}`">
        <i :class="icon" aria-hidden="true"></i>
      </div>
      <h3>{{ message }}</h3>
      <p v-if="description">{{ description }}</p>
    </div>

    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        text
        :disabled="busy"
        @click="$emit('cancel')"
      />
      <Button
        :label="confirmLabel"
        :icon="confirmIcon"
        severity="danger"
        :loading="busy"
        @click="$emit('confirm')"
      />
    </template>
  </Dialog>
</template>

<style scoped>
.confirm-dialog-content {
  padding: 0.5rem 0;
  text-align: center;
}

.confirm-dialog-icon {
  display: grid;
  width: 64px;
  height: 64px;
  margin: 0 auto 1.25rem;
  place-items: center;
  border-radius: 50%;
}

.confirm-dialog-icon--danger {
  background: var(--danger-subtle);
  color: var(--color-danger);
}

.confirm-dialog-icon--warning {
  background: var(--warning-subtle);
  color: var(--color-warning);
}

.confirm-dialog-icon i {
  font-size: 1.75rem;
}

h3 {
  margin: 0;
  color: var(--color-heading);
  font-size: 1.1rem;
  font-weight: 650;
  line-height: 1.45;
}

p {
  margin: 0.625rem auto 0;
  max-width: 340px;
  color: var(--color-text-mute);
  font-size: 0.9rem;
}
</style>
