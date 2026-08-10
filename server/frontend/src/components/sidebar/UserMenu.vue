<template>
  <div class="user-menu">
    <button
      type="button"
      class="user-trigger"
      :class="{ collapsed }"
      aria-haspopup="true"
      aria-controls="user_menu_overlay"
      @click="toggle"
      v-tooltip.right="collapsed ? `${username} (${roleLabel})` : null"
    >
      <span class="user-avatar" :class="authStore.isAdmin ? 'avatar-admin' : 'avatar-operator'">
        {{ initials }}
      </span>
      <span v-if="!collapsed" class="user-info">
        <span class="user-name">{{ username }}</span>
        <span class="user-role">{{ roleLabel }}</span>
      </span>
      <i v-if="!collapsed" class="pi pi-angle-up user-chevron"></i>
    </button>

    <Menu ref="menu" id="user_menu_overlay" :model="menuItems" :popup="true">
      <template #start>
        <div class="user-menu-header">
          <span class="user-avatar" :class="authStore.isAdmin ? 'avatar-admin' : 'avatar-operator'">
            {{ initials }}
          </span>
          <div class="user-menu-header-text">
            <strong>{{ username }}</strong>
            <span>{{ roleLabel }}</span>
          </div>
        </div>
      </template>
    </Menu>

  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Menu from 'primevue/menu'
import { useAuthStore } from '@/stores/auth'
import { backendService } from '@/services/backend'

defineProps({
  collapsed: { type: Boolean, default: false }
})

const router = useRouter()
const authStore = useAuthStore()
const menu = ref(null)

const username = computed(() => authStore.user?.username || '')
const roleLabel = computed(() => (authStore.user?.role === 'admin' ? 'Administrator' : 'Operator'))
const initials = computed(() => {
  const name = username.value.trim()
  return name ? name.charAt(0).toUpperCase() : '?'
})

function toggle(event) {
  menu.value.toggle(event)
}

async function handleLogout() {
  try {
    await backendService.logout()
  } finally {
    authStore.logout()
    router.push({ name: 'login' }).catch(() => {})
  }
}

const menuItems = ref([
  { separator: true },
  { label: 'Logout', icon: 'pi pi-sign-out', command: handleLogout, class: 'user-menu-logout-item' }
])
</script>

<style scoped>
.user-menu {
  width: 100%;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-height: 44px;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  transition:
    color var(--duration-normal) var(--ease-standard),
    background-color var(--duration-normal) var(--ease-standard),
    border-color var(--duration-normal) var(--ease-standard);
  text-align: left;
}

.user-trigger:hover {
  background: color-mix(in srgb, var(--color-heading) 6%, transparent);
}

.user-trigger.collapsed {
  justify-content: center;
  padding: 0.75rem;
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-inverse);
}

.avatar-admin {
  background: var(--color-warning);
}

.avatar-operator {
  background: var(--color-accent);
}

.user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 0.75rem;
  color: var(--color-text-mute);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-chevron {
  flex-shrink: 0;
  font-size: 0.875rem;
  color: var(--color-text-mute);
}

.user-menu-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 0.75rem;
}

.user-menu-header-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-menu-header-text strong {
  font-size: 0.875rem;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-menu-header-text span {
  font-size: 0.75rem;
  color: var(--color-text-mute);
}

/*
 * PrimeVue Menu teleports its popup to <body> by default, so it's no
 * longer a DOM descendant of this component once open — :deep() (which
 * relies on DOM ancestry) can never match it. :global() is required here.
 */
:global(.user-menu-logout-item .p-menu-item-link),
:global(.user-menu-logout-item .p-menu-item-content),
:global(.user-menu-logout-item .p-menu-item-label),
:global(.user-menu-logout-item .p-menu-item-icon) {
  color: var(--color-danger) !important;
}

:global(.user-menu-logout-item .p-menu-item-content:hover) {
  background: color-mix(in srgb, var(--color-danger) 10%, transparent) !important;
}
</style>
