<script setup>
defineProps({
  icon: {
    type: String,
    default: 'pi pi-inbox'
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'neutral',
    validator: (value) => ['neutral', 'danger'].includes(value)
  }
})
</script>

<template>
  <div class="empty-state" :class="`empty-state--${tone}`">
    <i :class="icon" aria-hidden="true"></i>
    <h2>{{ title }}</h2>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="empty-state-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  min-height: 280px;
  padding: 3rem 2rem;
  text-align: center;
  color: var(--color-text-mute);
}

.empty-state > i {
  margin-bottom: 0.5rem;
  font-size: 3rem;
  opacity: 0.55;
}

.empty-state--danger > i {
  color: var(--red-500);
  opacity: 0.85;
}

.empty-state h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 1.4rem;
  font-weight: 600;
}

.empty-state p {
  max-width: 560px;
  margin: 0;
}

.empty-state-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
</style>
