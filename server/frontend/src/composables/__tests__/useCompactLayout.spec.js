import { describe, expect, it, vi } from 'vitest'
import {
  COMPACT_VIEWPORT_QUERY,
  observeCompactViewport
} from '@/composables/useCompactLayout'

describe('observeCompactViewport', () => {
  it('reports the initial tablet state and subsequent viewport changes', () => {
    let listener
    const onChange = vi.fn()
    const media = {
      matches: true,
      addEventListener: vi.fn((event, callback) => { listener = callback }),
      removeEventListener: vi.fn()
    }
    const windowRef = { matchMedia: vi.fn(() => media) }

    const stop = observeCompactViewport(onChange, windowRef)
    listener({ matches: false })

    expect(windowRef.matchMedia).toHaveBeenCalledWith(COMPACT_VIEWPORT_QUERY)
    expect(onChange).toHaveBeenNthCalledWith(1, true)
    expect(onChange).toHaveBeenNthCalledWith(2, false)

    stop()
    expect(media.removeEventListener).toHaveBeenCalledWith('change', listener)
  })
})
