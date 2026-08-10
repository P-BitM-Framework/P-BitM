<template>
  <div
    class="delayed-content-shell"
    :class="{ 'is-loading': loading }"
    :aria-busy="loading"
    aria-live="polite"
  >
    <div v-if="loading" class="delayed-content-overlay">
      <ProgressSpinner
        v-if="showIndicator"
        class="delayed-content-spinner"
        aria-label="Loading"
      />
    </div>
    <div class="delayed-content-body">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  loading: {
    type: Boolean,
    required: true
  },
  showIndicator: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.delayed-content-shell {
  position: relative;
  min-height: calc(100vh - var(--page-padding) - var(--page-padding));
}

.delayed-content-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  min-height: 12rem;
  place-items: center;
  pointer-events: none;
}

.delayed-content-spinner {
  width: 2.5rem;
  height: 2.5rem;
}

.delayed-content-body {
  opacity: 1;
  transition: opacity 180ms var(--ease-standard);
}

.is-loading .delayed-content-body {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .delayed-content-body {
    transition: none;
  }
}
</style>
