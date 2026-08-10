<script setup>
defineProps({
  visible: Boolean,
  message: {
    type: String,
    default: 'Loading...'
  }
})

defineEmits(['update:visible'])
</script>

<template>
  <Dialog
    :visible="visible"
    :style="{ width: '380px' }"
    :closable="false"
    :draggable="false"
    modal
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="loader-dialog-content">
      <i class="pi pi-spin pi-spinner" aria-hidden="true"></i>
      <strong>{{ message }}</strong>
      <span>Please keep this window open.</span>
    </div>
  </Dialog>
</template>

<style scoped>
.loader-dialog-content {
  display: flex;
  min-height: 190px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.75rem;
  text-align: center;
}

.loader-dialog-content > i {
  margin-bottom: 0.5rem;
  color: var(--color-accent);
  font-size: 2.5rem;
}

.loader-dialog-content strong {
  max-width: 290px;
  color: var(--color-heading);
  font-size: 1.05rem;
  font-weight: 650;
  line-height: 1.4;
}

.loader-dialog-content span {
  color: var(--color-text-mute);
  font-size: 0.82rem;
}
</style>
