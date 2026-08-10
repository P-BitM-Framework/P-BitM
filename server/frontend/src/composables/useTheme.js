import { computed, readonly, ref } from 'vue'
import { updatePrimaryPalette } from '@primeuix/themes'

export const THEME_KEY = 'bitm-theme'
export const ACCENT_KEY = 'bitm-accent'
export const THEME_MODES = Object.freeze(['system', 'light', 'dark'])

export const ACCENT_OPTIONS = Object.freeze([
  {
    id: 'red', label: 'Red', preview: '#dc2626',
    light: { primary: '#dc2626', hover: '#e02d2d', active: '#b91c1c', on: '#ffffff' },
    dark: { primary: '#dc2626', hover: '#e02d2d', active: '#b91c1c', on: '#ffffff' },
    palette: { 50: '#fef2f2', 100: '#fee2e2', 200: '#fecaca', 300: '#fca5a5', 400: '#e02d2d', 500: '#dc2626', 600: '#b91c1c', 700: '#991b1b', 800: '#7f1d1d', 900: '#681919', 950: '#450a0a' }
  },
  {
    id: 'orange', label: 'Logo orange', preview: '#ee492a',
    light: { primary: '#ee492a', hover: '#f45f3d', active: '#e03f24', on: '#0c0c0f' },
    dark: { primary: '#ee492a', hover: '#f45f3d', active: '#e03f24', on: '#ffffff' },
    palette: { 50: '#fff4ef', 100: '#ffe2d5', 200: '#ffc5ad', 300: '#fda586', 400: '#fd926b', 500: '#ee492a', 600: '#d83b21', 700: '#b92f19', 800: '#942a1b', 900: '#77261c', 950: '#401008' }
  },
  {
    id: 'emerald', label: 'Emerald green', preview: '#10b981',
    light: { primary: '#10b981', hover: '#34d399', active: '#0ea875', on: '#0c0c0f' },
    dark: { primary: '#10b981', hover: '#34d399', active: '#0ea875', on: '#ffffff' },
    palette: { 50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0', 300: '#6ee7b7', 400: '#34d399', 500: '#10b981', 600: '#059669', 700: '#047857', 800: '#065f46', 900: '#064e3b', 950: '#022c22' }
  },
  {
    id: 'blue', label: 'Classic blue', preview: '#3b82f6',
    light: { primary: '#3b82f6', hover: '#60a5fa', active: '#387fee', on: '#0c0c0f' },
    dark: { primary: '#3b82f6', hover: '#60a5fa', active: '#387fee', on: '#ffffff' },
    palette: { 50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a', 950: '#172554' }
  },
  {
    id: 'violet', label: 'Violet', preview: '#8b5cf6',
    light: { primary: '#8b5cf6', hover: '#a78bfa', active: '#8a5bf2', on: '#0c0c0f' },
    dark: { primary: '#8b5cf6', hover: '#a78bfa', active: '#8a5bf2', on: '#ffffff' },
    palette: { 50: '#f5f3ff', 100: '#ede9fe', 200: '#ddd6fe', 300: '#c4b5fd', 400: '#a78bfa', 500: '#8b5cf6', 600: '#7c3aed', 700: '#6d28d9', 800: '#5b21b6', 900: '#4c1d95', 950: '#2e1065' }
  }
])

const LEGACY_ACCENTS = Object.freeze({
  cobalt: 'blue', indigo: 'blue', sky: 'blue', cyan: 'emerald', teal: 'emerald',
  green: 'emerald', mint: 'emerald', purple: 'violet', pink: 'violet', rose: 'violet',
  steel: 'violet', graphite: 'violet', amber: 'orange', peach: 'orange'
})

const mode = ref('system')
const resolvedTheme = ref('light')
const accent = ref('orange')
let mediaQuery = null
let mediaListener = null

function isThemeMode(value) {
  return THEME_MODES.includes(value)
}

function resolveTheme(nextMode = mode.value) {
  if (nextMode !== 'system') return nextMode
  return mediaQuery?.matches ? 'dark' : 'light'
}

function getAccentOption(accentId = accent.value) {
  return ACCENT_OPTIONS.find((option) => option.id === accentId)
    || ACCENT_OPTIONS.find((option) => option.id === 'orange')
}

function applyAccent(nextTheme = resolvedTheme.value) {
  const option = getAccentOption()
  const colors = option[nextTheme]
  const root = document.documentElement

  updatePrimaryPalette(option.palette)
  root.dataset.accent = option.id
  root.style.setProperty('--primary', colors.primary)
  root.style.setProperty('--primary-hover', colors.hover)
  root.style.setProperty('--primary-active', colors.active)
  root.style.setProperty('--primary-on', colors.on)
  root.style.setProperty('--focus-ring', colors.primary)
  root.style.setProperty('--p-primary-color', colors.primary)
  root.style.setProperty('--p-primary-hover-color', colors.hover)
  root.style.setProperty('--p-primary-active-color', colors.active)
  root.style.setProperty('--p-primary-contrast-color', colors.on)
  root.style.setProperty('--p-focus-ring-color', colors.primary)
  root.style.setProperty('--p-form-field-focus-border-color', colors.primary)
}

function applyTheme() {
  const nextTheme = resolveTheme()
  resolvedTheme.value = nextTheme

  const root = document.documentElement
  root.classList.toggle('dark-mode', nextTheme === 'dark')
  root.classList.toggle('light-mode', nextTheme === 'light')
  root.dataset.theme = nextTheme
  root.style.colorScheme = nextTheme
  applyAccent(nextTheme)
  const themeColor = document.querySelector('meta[name="theme-color"]')
  if (themeColor) {
    themeColor.setAttribute('content', nextTheme === 'dark' ? '#0c0c0f' : '#f7f7f8')
  }
}

function detachMediaListener() {
  if (!mediaQuery || !mediaListener) return
  if (typeof mediaQuery.removeEventListener === 'function') {
    mediaQuery.removeEventListener('change', mediaListener)
  } else if (typeof mediaQuery.removeListener === 'function') {
    mediaQuery.removeListener(mediaListener)
  }
  mediaListener = null
}

export function initializeTheme() {
  detachMediaListener()
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

  const savedMode = localStorage.getItem(THEME_KEY)
  const savedAccent = localStorage.getItem(ACCENT_KEY)
  const normalizedAccent = LEGACY_ACCENTS[savedAccent] || savedAccent
  mode.value = isThemeMode(savedMode) ? savedMode : 'system'
  accent.value = ACCENT_OPTIONS.some((option) => option.id === normalizedAccent) ? normalizedAccent : 'orange'
  if (!isThemeMode(savedMode) && savedMode !== null) {
    localStorage.removeItem(THEME_KEY)
  }
  if (LEGACY_ACCENTS[savedAccent]) {
    localStorage.setItem(ACCENT_KEY, normalizedAccent)
  } else if (savedAccent !== null && !ACCENT_OPTIONS.some((option) => option.id === savedAccent)) {
    localStorage.removeItem(ACCENT_KEY)
  }

  mediaListener = () => {
    if (mode.value === 'system') applyTheme()
  }

  if (typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', mediaListener)
  } else if (typeof mediaQuery.addListener === 'function') {
    mediaQuery.addListener(mediaListener)
  }

  applyTheme()
  return disposeTheme
}

export function disposeTheme() {
  detachMediaListener()
  mediaQuery = null
}

export function setThemeMode(nextMode) {
  if (!isThemeMode(nextMode)) {
    throw new TypeError(`Unsupported theme mode: ${nextMode}`)
  }

  mode.value = nextMode
  if (nextMode === 'system') {
    localStorage.removeItem(THEME_KEY)
  } else {
    localStorage.setItem(THEME_KEY, nextMode)
  }
  applyTheme()
}

export function setAccent(nextAccent) {
  if (!ACCENT_OPTIONS.some((option) => option.id === nextAccent)) {
    throw new TypeError(`Unsupported accent: ${nextAccent}`)
  }

  accent.value = nextAccent
  localStorage.setItem(ACCENT_KEY, nextAccent)
  applyAccent()
}

export function useTheme() {
  return {
    mode: readonly(mode),
    accent: readonly(accent),
    accentOptions: ACCENT_OPTIONS,
    resolvedTheme: readonly(resolvedTheme),
    isDark: computed(() => resolvedTheme.value === 'dark'),
    setThemeMode,
    setAccent
  }
}
