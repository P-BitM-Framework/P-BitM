import { effectScope, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

describe('useDelayedIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not flash for work completed before the delay', () => {
    const scope = effectScope()
    const loading = ref(true)
    const visible = scope.run(() => useDelayedIndicator(loading, 300))

    vi.advanceTimersByTime(200)
    loading.value = false

    expect(visible.value).toBe(false)
    vi.advanceTimersByTime(200)
    expect(visible.value).toBe(false)
    scope.stop()
  })

  it('appears after the delay and hides immediately on completion', () => {
    const scope = effectScope()
    const loading = ref(true)
    const visible = scope.run(() => useDelayedIndicator(loading, 300))

    vi.advanceTimersByTime(300)
    expect(visible.value).toBe(true)

    loading.value = false
    expect(visible.value).toBe(false)
    scope.stop()
  })
})
