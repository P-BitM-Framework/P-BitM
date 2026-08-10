<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Header con Logo -->
    <div class="sidebar-header">
      <button
        type="button"
        class="logo-container"
        aria-label="Go to campaigns"
        @click="router.push({ name: 'campaigns' })"
      >
        <img
          alt="BitM logo"
          src="@/assets/images/logo.webp"
          class="logo"
        />
      </button>
    </div>

    <!-- Navigation -->
    <nav id="primary-navigation" class="sidebar-nav">
      <div
        v-for="(section, sectionIndex) in menuSections"
        :key="sectionIndex"
        class="nav-section"
      >
        <!-- Section Label -->
        <div v-if="section.label && !isCollapsed" class="nav-section-label">
          {{ section.label }}
        </div>

        <!-- Section Items -->
        <ul class="nav-list">
          <li
            v-for="item in section.items"
            :key="item.route"
            class="nav-list-item"
          >
            <button
              type="button"
              class="nav-item"
              :class="{ active: isActive(item) }"
              :disabled="item.disabled"
              :aria-current="isActive(item) ? 'page' : undefined"
              @click="navigate(item)"
              @mouseenter="preloadRouteComponent(item.route).catch(() => {})"
              @focus="preloadRouteComponent(item.route).catch(() => {})"
              v-tooltip.right="isCollapsed ? item.label : null"
            >
              <Icon v-if="item.iconifyIcon" :icon="item.iconifyIcon" :width="20" />
              <i v-else :class="item.icon"></i>
              <span class="nav-label">{{ item.label }}</span>
              <span v-if="item.badge && item.badge() > 0 && !isCollapsed" class="badge-active">
                {{ item.badge() }}
              </span>
              <span v-if="item.disabled && !isCollapsed" class="badge-soon">Soon</span>
            </button>
          </li>
        </ul>

        <!-- Divider -->
        <div
          v-if="sectionIndex < menuSections.length - 1"
          class="nav-divider"
        ></div>
      </div>
    </nav>

    <!-- Footer -->
    <div class="sidebar-footer">
      <button
        type="button"
        class="sidebar-toggle"
        :class="{ collapsed: isCollapsed }"
        :aria-label="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!isCollapsed"
        aria-controls="primary-navigation"
        @click="toggleSidebar"
        v-tooltip.right="isCollapsed ? 'Expand sidebar' : null"
      >
        <i
          :class="isCollapsed ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'"
          aria-hidden="true"
        ></i>
        <span v-if="!isCollapsed">Collapse sidebar</span>
      </button>

      <!-- Theme Toggle -->
      <SwitchTheme
        :collapsed="isCollapsed"
        v-tooltip.right="isCollapsed ? 'Appearance' : null"
      />

      <!-- User Menu -->
      <UserMenu :collapsed="isCollapsed" />
    </div>
  </aside>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SwitchTheme from '@/components/sidebar/SwitchTheme.vue'
import UserMenu from '@/components/sidebar/UserMenu.vue'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '@/stores/auth'
import { preloadRouteComponent } from '@/router'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const props = defineProps({
  collapsed: { type: Boolean, default: false }
})
const emit = defineEmits(['update:collapsed'])

const isCollapsed = computed({
  get: () => props.collapsed,
  set: (val) => emit('update:collapsed', val)
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

// Menu Structure
const menuSections = computed(() => {
  const sections = [
    {
      label: null,
      items: [
        {
          label: 'Campaigns',
          icon: 'pi pi-flag',
          route: 'campaigns',
          disabled: false
        }
      ]
    },
    {
      label: 'Campaign Setup',
      items: [
        { label: 'Target Lists', icon: 'pi pi-users', route: 'target-lists', disabled: false },
        { label: 'Email Templates', icon: 'pi pi-envelope', route: 'email-templates', disabled: false },
        { label: 'Landing Pages', icon: 'pi pi-globe', route: 'landing-pages', disabled: false },
        { label: 'SMTP Profiles', icon: 'pi pi-send', route: 'smtp-profiles', disabled: false }
      ]
    },
    {
      label: 'Attack Vectors',
      items: [
        { label: 'Modules', icon: 'pi pi-bolt', route: 'modules', disabled: false },
        { label: 'Browser Extensions', iconifyIcon: 'mdi:firefox', route: 'plugins', disabled: false }
      ]
    }
  ]

  if (authStore.isAdmin) {
    sections.push({
      label: 'Administration',
      items: [
        { label: 'Team', icon: 'pi pi-id-card', route: 'users', disabled: false }
      ]
    })
  }

  return sections
})

function navigate(item) {
  if (!item.disabled) {
    router.push({ name: item.route })
  }
}

function isActive(item) {
  if (route.name === item.route) return true

  const routeRelations = {
    'campaigns': ['campaign', 'victim'],
    'target-lists': ['target-list'],
    'plugins': ['plugin-editor']
  }

  const relatedRoutes = routeRelations[item.route] || []
  return relatedRoutes.includes(route.name)
}

onMounted(() => {
  const savedState = localStorage.getItem('sidebar-collapsed')
  if (savedState !== null) {
    isCollapsed.value = savedState === 'true'
  }
})

watch(isCollapsed, (value) => {
  localStorage.setItem('sidebar-collapsed', String(value))
})

</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--surface-card);
  border-right: 1px solid var(--color-border);
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1000;
  box-shadow: var(--shadow-sm);
  transition: width var(--duration-normal) var(--ease-standard);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

/* Header */
.sidebar-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 142px;
  padding: 1rem 1.25rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.sidebar.collapsed .sidebar-header {
  flex-direction: column;
  justify-content: center;
  gap: 0.625rem;
  min-height: 92px;
  padding: 0.75rem;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

.logo {
  width: 112px;
  height: 112px;
  max-width: 100%;
  object-fit: contain;
  transition:
    width var(--duration-normal) var(--ease-standard),
    height var(--duration-normal) var(--ease-standard);
}

.sidebar.collapsed .logo {
  width: 52px;
  height: 52px;
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  padding: 0.875rem 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-section {
  margin-bottom: 0.5rem;
}

.nav-section-label {
  padding: 0.75rem 1.5rem 0.5rem;
  font-size: 0.688rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-mute);
  opacity: 0.7;
  margin-top: 0.5rem;
  white-space: nowrap;
  transition: opacity 0.3s ease;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0 0.875rem;
}

.nav-list-item {
  margin: 0 0 0.2rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  min-height: 44px;
  padding: 0.7rem 0.875rem;
  width: 100%;
  margin: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  color: var(--color-text);
  font-size: 0.938rem;
  font-weight: 500;
  text-align: left;
  transition:
    color var(--duration-normal) var(--ease-standard),
    background-color var(--duration-normal) var(--ease-standard),
    border-color var(--duration-normal) var(--ease-standard);
  position: relative;
  white-space: nowrap;
}

.nav-item i {
  font-size: 1.125rem;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.nav-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.3s ease, width 0.3s ease;
}

.nav-item:hover:not(:disabled) {
  background-color: var(--color-background-mute);
}

.nav-item:hover:not(:disabled) i {
  transform: scale(1.1);
}

.nav-item.active {
  border-color: color-mix(in srgb, var(--color-accent) 35%, transparent);
  background: var(--color-accent-subtle);
  color: var(--color-accent);
  font-weight: 600;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-accent);
  border-radius: 0 4px 4px 0;
}

.nav-item:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Badges */
.badge-active {
  font-size: 0.688rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-success);
  color: white;
  border-radius: 12px;
  font-weight: 700;
  line-height: 1;
  min-width: 20px;
  text-align: center;
  transition: opacity 0.3s ease;
}

.badge-soon {
  font-size: 0.625rem;
  padding: 0.25rem 0.5rem;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text-mute);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
  transition: opacity 0.3s ease;
}

/* Divider */
.nav-divider {
  height: 1px;
  background: var(--color-border);
  margin: 0.75rem 1.5rem;
}

/* Footer */
.sidebar-footer {
  padding: 0.875rem;
  border-top: 1px solid var(--color-border);
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  min-height: 42px;
  padding: 0.45rem 0.625rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  text-align: left;
  transition:
    color var(--duration-normal) var(--ease-standard),
    background-color var(--duration-normal) var(--ease-standard);
}

.sidebar-toggle:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.sidebar-toggle i {
  width: 20px;
  color: var(--text-muted);
  font-size: 0.9rem;
  text-align: center;
}

.sidebar-toggle:hover i {
  color: var(--primary);
}

.sidebar-toggle.collapsed {
  justify-content: center;
  padding-inline: 0;
}

/* Collapsed State */
.sidebar.collapsed .nav-label,
.sidebar.collapsed .nav-section-label,
.sidebar.collapsed .badge-active,
.sidebar.collapsed .badge-soon {
  display: none;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.75rem;
}

/* Scrollbar */
.sidebar-nav::-webkit-scrollbar {
  width: 5px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 10px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-mute);
}

@media (max-width: 1199px) {
  .sidebar:not(.collapsed) {
    box-shadow: var(--shadow-lg);
  }

  .sidebar.collapsed .sidebar-header {
    min-height: 82px;
  }

  .sidebar.collapsed .logo {
    width: 44px;
    height: 44px;
  }
}

</style>
