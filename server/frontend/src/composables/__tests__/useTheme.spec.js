import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ACCENT_KEY,
  ACCENT_OPTIONS,
  THEME_KEY,
  disposeTheme,
  initializeTheme,
  setAccent,
  setThemeMode,
  useTheme
} from '@/composables/useTheme'

describe('useTheme', () => {
  let media
  let listeners

  beforeEach(() => {
    listeners = new Set()
    media = {
      matches: false,
      addEventListener: vi.fn((event, listener) => listeners.add(listener)),
      removeEventListener: vi.fn((event, listener) => listeners.delete(listener))
    }
    vi.stubGlobal('matchMedia', vi.fn(() => media))
    localStorage.clear()
    document.documentElement.className = ''
    delete document.documentElement.dataset.theme
    document.head.innerHTML = '<meta name="theme-color" content="#f7f7f8">'
  })

  afterEach(() => {
    disposeTheme()
    vi.unstubAllGlobals()
  })

  it('follows the system when no explicit preference exists', () => {
    media.matches = true
    initializeTheme()

    const theme = useTheme()
    expect(theme.mode.value).toBe('system')
    expect(theme.resolvedTheme.value).toBe('dark')
    expect(theme.accent.value).toBe('orange')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
  })

  it('preserves legacy light and dark preferences', () => {
    localStorage.setItem(THEME_KEY, 'dark')
    initializeTheme()

    expect(useTheme().mode.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('persists explicit choices and removes storage for system mode', () => {
    initializeTheme()
    setThemeMode('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')

    setThemeMode('system')
    expect(localStorage.getItem(THEME_KEY)).toBeNull()
  })

  it('keeps the browser chrome color aligned with the resolved theme', () => {
    initializeTheme()
    setThemeMode('dark')
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#0c0c0f')

    setThemeMode('light')
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#f7f7f8')
  })

  it('reacts to system changes only while using system mode', () => {
    initializeTheme()
    media.matches = true
    listeners.forEach((listener) => listener({ matches: true }))
    expect(document.documentElement.dataset.theme).toBe('dark')

    setThemeMode('light')
    media.matches = false
    listeners.forEach((listener) => listener({ matches: false }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('cleans up the system preference listener', () => {
    initializeTheme()
    disposeTheme()
    expect(media.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    expect(listeners.size).toBe(0)
  })

  it('persists a security accent and applies it to app and PrimeVue tokens', () => {
    initializeTheme()
    setAccent('orange')

    const rootStyle = document.documentElement.style
    expect(localStorage.getItem(ACCENT_KEY)).toBe('orange')
    expect(document.documentElement.dataset.accent).toBe('orange')
    expect(rootStyle.getPropertyValue('--primary')).toBe('#ee492a')
    expect(rootStyle.getPropertyValue('--p-primary-color')).toBe('#ee492a')
  })

  it('keeps the original app blue as the actual classic blue accent', () => {
    initializeTheme()
    setAccent('blue')

    const rootStyle = document.documentElement.style
    expect(rootStyle.getPropertyValue('--primary')).toBe('#3b82f6')
    expect(rootStyle.getPropertyValue('--p-primary-color')).toBe('#3b82f6')
  })

  it('uses the dark variant of the selected accent when the theme changes', () => {
    localStorage.setItem(ACCENT_KEY, 'emerald')
    initializeTheme()
    setThemeMode('dark')

    expect(document.documentElement.style.getPropertyValue('--primary')).toBe('#10b981')
    expect(document.documentElement.style.getPropertyValue('--primary-on')).toBe('#ffffff')
    expect(document.documentElement.style.getPropertyValue('--p-primary-contrast-color')).toBe('#ffffff')
  })

  it('uses white button text for every accent in dark mode', () => {
    expect(ACCENT_OPTIONS.every((option) => option.dark.on === '#ffffff')).toBe(true)
  })

  it('falls back to orange for an invalid saved accent', () => {
    localStorage.setItem(ACCENT_KEY, 'unknown')
    initializeTheme()

    expect(useTheme().accent.value).toBe('orange')
    expect(localStorage.getItem(ACCENT_KEY)).toBeNull()
  })

  it('exposes five distinct accents in chromatic order', () => {
    expect(ACCENT_OPTIONS.map((option) => option.id)).toEqual([
      'red', 'orange', 'emerald', 'blue', 'violet'
    ])
  })

  it('migrates the previous pastel accent names', () => {
    localStorage.setItem(ACCENT_KEY, 'mint')
    initializeTheme()

    expect(useTheme().accent.value).toBe('emerald')
    expect(localStorage.getItem(ACCENT_KEY)).toBe('emerald')
  })
})
