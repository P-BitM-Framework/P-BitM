<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import { RouterView, useRoute } from 'vue-router'
import { preloadAuthenticatedRoutes } from '@/router'
import { observeCompactViewport } from '@/composables/useCompactLayout'

const auth = useAuthStore()
const route = useRoute()
const isSidebarCollapsed = ref(false)
const isCompactViewport = ref(false)
let preloadHandle = null
let stopCompactViewportObserver = null

function scheduleRoutePreload() {
  if (!auth.isAuthenticated || preloadHandle !== null) return

  if ('requestIdleCallback' in window) {
    preloadHandle = window.requestIdleCallback(
      () => preloadAuthenticatedRoutes(),
      { timeout: 1200 }
    )
  } else {
    preloadHandle = window.setTimeout(() => preloadAuthenticatedRoutes(), 300)
  }
}

function syncCompactViewport(matches) {
  isCompactViewport.value = matches
  if (matches) isSidebarCollapsed.value = true
}

function handleGlobalKeydown(event) {
  if (event.key === 'Escape' && isCompactViewport.value && !isSidebarCollapsed.value) {
    isSidebarCollapsed.value = true
  }
}

onMounted(() => {
  scheduleRoutePreload()
  stopCompactViewportObserver = observeCompactViewport(syncCompactViewport)
  window.addEventListener('keydown', handleGlobalKeydown)
})

watch(() => auth.isAuthenticated, (isAuthenticated) => {
  if (isAuthenticated) scheduleRoutePreload()
})

watch(() => route.fullPath, () => {
  if (isCompactViewport.value) isSidebarCollapsed.value = true
})

onUnmounted(() => {
  stopCompactViewportObserver?.()
  window.removeEventListener('keydown', handleGlobalKeydown)
  if (preloadHandle === null) return
  if ('cancelIdleCallback' in window) {
    window.cancelIdleCallback(preloadHandle)
  } else {
    window.clearTimeout(preloadHandle)
  }
})
</script>

<template>
  <div
    v-if="auth.isAuthenticated"
    class="app-layout"
    :class="{ 'compact-viewport': isCompactViewport }"
  >
    <Sidebar v-model:collapsed="isSidebarCollapsed" />
    <button
      v-if="isCompactViewport && !isSidebarCollapsed"
      type="button"
      class="sidebar-backdrop"
      aria-label="Close navigation"
      @click="isSidebarCollapsed = true"
    ></button>
    <main class="main-content" :class="{ collapsed: isSidebarCollapsed }">
      <Toast />
      <RouterView v-slot="{ Component, route }">
        <div :key="String(route.name)">
          <component :is="Component" />
        </div>
      </RouterView>
    </main>
  </div>
  <div v-else>
    <RouterView v-slot="{ Component, route }">
      <div :key="route.fullPath">
        <component :is="Component" />
      </div>
    </RouterView>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--surface-canvas);
}

.main-content {
  flex: 1;
  min-width: 0;
  margin-left: var(--sidebar-width);
  background: var(--surface-canvas);
  transition: margin-left var(--duration-normal) var(--ease-standard);
}

.main-content.collapsed {
  --content-max-width: calc(
    var(--content-base-max-width) + var(--sidebar-width) - var(--sidebar-collapsed-width)
  );
  margin-left: var(--sidebar-collapsed-width);
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 999;
  padding: 0;
  border: 0;
  background: var(--surface-overlay);
  backdrop-filter: blur(3px);
  cursor: default;
}

@media (max-width: 1199px) {
  .compact-viewport .main-content {
    --content-max-width: calc(
      var(--content-base-max-width) + var(--sidebar-width) - var(--sidebar-collapsed-width)
    );
  }

  .main-content,
  .main-content.collapsed {
    margin-left: var(--sidebar-collapsed-width);
  }
}

</style>
