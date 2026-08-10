<template>
  <div class="theme-selector">
    <button
      type="button"
      class="theme-trigger"
      :class="{ collapsed }"
      aria-haspopup="menu"
      aria-controls="theme_menu_overlay"
      :aria-label="`Appearance: ${currentLabel}`"
      @click="toggleMenu"
    >
      <i :class="currentIcon" aria-hidden="true"></i>
      <span v-if="!collapsed" class="theme-label">
        <span>Appearance</span>
        <small>{{ currentLabel }}</small>
      </span>
      <i v-if="!collapsed" class="pi pi-angle-up theme-chevron" aria-hidden="true"></i>
    </button>

    <Menu ref="menu" id="theme_menu_overlay" :model="menuItems" :popup="true">
      <template #item="{ item, props: itemProps }">
        <a v-bind="itemProps.action" :aria-current="mode === item.value ? 'true' : undefined">
          <i :class="item.icon" aria-hidden="true"></i>
          <span class="p-menu-item-label">{{ item.label }}</span>
          <i v-if="mode === item.value" class="pi pi-check theme-check" aria-hidden="true"></i>
        </a>
      </template>
      <template #end>
        <div class="accent-picker" @click.stop>
          <span class="accent-picker-label">Accent color</span>
          <div class="accent-swatches" role="radiogroup" aria-label="Accent color">
            <button
              v-for="option in accentOptions"
              :key="option.id"
              type="button"
              class="accent-swatch"
              :class="{ selected: accent === option.id }"
              :style="{ '--swatch-color': option.preview }"
              role="radio"
              :aria-checked="accent === option.id"
              :aria-label="option.label"
              :title="option.label"
              @click="setAccent(option.id)"
            >
              <span class="sr-only">{{ option.label }}</span>
            </button>
          </div>
        </div>
      </template>
    </Menu>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Menu from 'primevue/menu'
import { useTheme } from '@/composables/useTheme'

defineProps({
  collapsed: { type: Boolean, default: false }
})

const menu = ref(null)
const { mode, resolvedTheme, accent, accentOptions, setThemeMode, setAccent } = useTheme()

const choices = [
  { label: 'System', value: 'system', icon: 'pi pi-desktop' },
  { label: 'Light', value: 'light', icon: 'pi pi-sun' },
  { label: 'Dark', value: 'dark', icon: 'pi pi-moon' }
]

const currentChoice = computed(() => choices.find((choice) => choice.value === mode.value))
const currentLabel = computed(() => mode.value === 'system'
  ? `System · ${resolvedTheme.value === 'dark' ? 'Dark' : 'Light'}`
  : currentChoice.value.label)
const currentIcon = computed(() => currentChoice.value.icon)
const menuItems = computed(() => choices.map((choice) => ({
  ...choice,
  command: () => setThemeMode(choice.value)
})))

function toggleMenu(event) {
  menu.value.toggle(event)
}
</script>

<style scoped>
.theme-selector {
  width: 100%;
}

.theme-trigger {
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
  text-align: left;
  transition:
    color var(--duration-normal) var(--ease-standard),
    background-color var(--duration-normal) var(--ease-standard),
    border-color var(--duration-normal) var(--ease-standard);
}

.theme-trigger:hover,
.theme-trigger[aria-expanded='true'] {
  border-color: var(--border-subtle);
  background: var(--surface-hover);
  color: var(--text-primary);
}

.theme-trigger.collapsed {
  justify-content: center;
  padding-inline: 0;
}

.theme-trigger > .pi:first-child {
  width: 20px;
  color: var(--primary);
  font-size: 1rem;
  text-align: center;
}

.theme-label {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.theme-label > span {
  color: var(--text-primary);
  font-size: 0.84rem;
  font-weight: 600;
}

.theme-label small {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.7rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-chevron {
  color: var(--text-muted);
  font-size: 0.72rem;
}

:global(#theme_menu_overlay) {
  min-width: 220px;
}

:global(#theme_menu_overlay .p-menu-item-link) {
  display: flex;
  gap: 0.7rem;
  color: var(--text-secondary);
}

:global(#theme_menu_overlay .p-menu-item-link > i:first-child),
:global(#theme_menu_overlay .p-menu-item-label) {
  color: var(--text-secondary);
}

:global(#theme_menu_overlay .p-menu-item-link:hover),
:global(#theme_menu_overlay .p-menu-item-link:focus-visible),
:global(#theme_menu_overlay .p-menu-item-link:hover > i:first-child),
:global(#theme_menu_overlay .p-menu-item-link:focus-visible > i:first-child),
:global(#theme_menu_overlay .p-menu-item-link:hover .p-menu-item-label),
:global(#theme_menu_overlay .p-menu-item-link:focus-visible .p-menu-item-label) {
  color: var(--text-primary);
}

:global(#theme_menu_overlay .theme-check) {
  margin-left: auto;
  color: var(--primary);
}

.accent-picker {
  margin-top: 0.25rem;
  padding: 0.75rem;
  border-top: 1px solid var(--border-subtle);
}

.accent-picker-label {
  display: block;
  margin-bottom: 0.625rem;
  color: var(--text-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.accent-swatches {
  display: grid;
  grid-template-columns: repeat(5, 26px);
  gap: 0.75rem 0.625rem;
  justify-content: space-between;
}

.accent-swatch {
  position: relative;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 3px solid var(--surface-raised);
  border-radius: 50%;
  background: var(--swatch-color);
  box-shadow: 0 0 0 1px var(--border-default);
  cursor: pointer;
  transition:
    box-shadow var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}

.accent-swatch:hover {
  transform: scale(1.1);
}

.accent-swatch.selected {
  box-shadow:
    0 0 0 2px var(--surface-raised),
    0 0 0 4px var(--swatch-color);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
