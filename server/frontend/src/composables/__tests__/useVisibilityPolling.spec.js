import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'

function createHarness(task, options) {
  return defineComponent({
    setup() {
      return useVisibilityPolling(task, options)
    },
    template: '<div />'
  })
}

function abortableTask(signals) {
  return vi.fn((signal) => {
    signals.push(signal)
    return new Promise((_resolve, reject) => {
      signal.addEventListener(
        'abort',
        () => reject(new DOMException('Aborted', 'AbortError')),
        { once: true }
      )
    })
  })
}

describe('useVisibilityPolling', () => {
  let hidden

  beforeEach(() => {
    vi.useFakeTimers()
    hidden = false
    vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('runs immediately and then at the configured interval', async () => {
    const task = vi.fn().mockResolvedValue(undefined)
    const Harness = createHarness(task, { intervalMs: 1000 })
    const wrapper = mount(Harness)

    expect(task).toHaveBeenCalledOnce()
    expect(task.mock.calls[0][0]).toBeInstanceOf(AbortSignal)

    await flushPromises()
    await vi.advanceTimersByTimeAsync(3000)

    expect(task).toHaveBeenCalledTimes(4)
    wrapper.unmount()
  })

  it('does not overlap refreshes when a previous request is pending', async () => {
    let resolveRequest
    const task = vi.fn(
      () => new Promise((resolve) => {
        resolveRequest = resolve
      })
    )
    const Harness = createHarness(task, { intervalMs: 500 })
    const wrapper = mount(Harness)

    await vi.advanceTimersByTimeAsync(2000)
    expect(task).toHaveBeenCalledOnce()

    resolveRequest()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(500)

    expect(task).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('aborts the active request while hidden and restarts when visible', async () => {
    const signals = []
    const task = abortableTask(signals)
    const Harness = createHarness(task, { intervalMs: 1000 })
    const wrapper = mount(Harness)

    expect(task).toHaveBeenCalledOnce()
    hidden = true
    document.dispatchEvent(new Event('visibilitychange'))

    expect(signals[0].aborted).toBe(true)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(3000)
    expect(task).toHaveBeenCalledOnce()

    hidden = false
    document.dispatchEvent(new Event('visibilitychange'))
    expect(task).toHaveBeenCalledTimes(2)

    wrapper.unmount()
  })

  it('reacts to a dynamic enabled flag and cancels work when disabled', async () => {
    const enabled = ref(false)
    const signals = []
    const task = abortableTask(signals)
    const Harness = createHarness(task, {
      intervalMs: 1000,
      enabled
    })
    const wrapper = mount(Harness)

    expect(task).not.toHaveBeenCalled()

    enabled.value = true
    await nextTick()
    expect(task).toHaveBeenCalledOnce()

    enabled.value = false
    await nextTick()
    expect(signals[0].aborted).toBe(true)

    await flushPromises()
    await vi.advanceTimersByTimeAsync(2000)
    expect(task).toHaveBeenCalledOnce()

    wrapper.unmount()
  })

  it('supports a non-immediate first run', async () => {
    const task = vi.fn().mockResolvedValue(undefined)
    const Harness = createHarness(task, {
      intervalMs: 750,
      immediate: false
    })
    const wrapper = mount(Harness)

    expect(task).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(750)
    expect(task).toHaveBeenCalledOnce()

    wrapper.unmount()
  })

  it('stops and restarts polling through the returned controls', async () => {
    const task = vi.fn().mockResolvedValue(undefined)
    const Harness = createHarness(task, { intervalMs: 1000 })
    const wrapper = mount(Harness)
    await flushPromises()

    wrapper.vm.stop()
    await vi.advanceTimersByTimeAsync(3000)
    expect(task).toHaveBeenCalledOnce()

    wrapper.vm.start(true)
    expect(task).toHaveBeenCalledTimes(2)

    wrapper.unmount()
  })

  it('aborts active work and removes the visibility listener on unmount', () => {
    const signals = []
    const task = abortableTask(signals)
    const removeEventListener = vi.spyOn(document, 'removeEventListener')
    const Harness = createHarness(task, { intervalMs: 1000 })
    const wrapper = mount(Harness)

    wrapper.unmount()

    expect(signals[0].aborted).toBe(true)
    expect(removeEventListener).toHaveBeenCalledWith(
      'visibilitychange',
      expect.any(Function)
    )
    expect(vi.getTimerCount()).toBe(0)
  })

  it('logs task failures but ignores AbortError as expected cancellation', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {})
    const failure = new Error('network unavailable')
    const failingTask = vi.fn().mockRejectedValue(failure)
    const FailingHarness = createHarness(failingTask, {
      intervalMs: 1000
    })
    const failingWrapper = mount(FailingHarness)

    await flushPromises()
    expect(consoleError).toHaveBeenCalledWith(
      'Background refresh failed:',
      failure
    )
    failingWrapper.unmount()

    consoleError.mockClear()
    const abortingTask = vi
      .fn()
      .mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    const AbortingHarness = createHarness(abortingTask, {
      intervalMs: 1000
    })
    const abortingWrapper = mount(AbortingHarness)

    await flushPromises()
    expect(consoleError).not.toHaveBeenCalled()
    abortingWrapper.unmount()
  })
})
