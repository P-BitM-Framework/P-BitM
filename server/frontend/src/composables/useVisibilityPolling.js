import {
  onActivated,
  onDeactivated,
  onMounted,
  onUnmounted,
  toValue,
  watch
} from 'vue'

/**
 * Run one non-overlapping polling task only while its view is active.
 *
 * The task receives an AbortSignal. Hiding, deactivating, or unmounting the
 * view cancels the active request and clears its timer.
 */
export function useVisibilityPolling(task, {
  intervalMs,
  enabled = true,
  immediate = true
}) {
  let timer = null
  let controller = null
  let running = false
  let viewActive = true

  const canRun = () => (
    viewActive
    && !document.hidden
    && Boolean(toValue(enabled))
  )

  async function refresh() {
    if (!canRun() || running) return

    running = true
    const requestController = new AbortController()
    controller = requestController

    try {
      await task(requestController.signal)
    } catch (error) {
      if (error?.name !== 'AbortError') {
        console.error('Background refresh failed:', error)
      }
    } finally {
      if (controller === requestController) {
        controller = null
      }
      running = false
    }
  }

  function start(runImmediately = immediate) {
    if (!canRun() || timer !== null) return
    if (runImmediately) void refresh()
    timer = window.setInterval(() => void refresh(), intervalMs)
  }

  function stop() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
    controller?.abort()
    controller = null
  }

  function sync() {
    if (canRun()) start(true)
    else stop()
  }

  function handleVisibilityChange() {
    sync()
  }

  onMounted(() => {
    viewActive = true
    document.addEventListener('visibilitychange', handleVisibilityChange)
    start()
  })

  onActivated(() => {
    viewActive = true
    start(true)
  })

  onDeactivated(() => {
    viewActive = false
    stop()
  })

  watch(() => Boolean(toValue(enabled)), sync)

  onUnmounted(() => {
    viewActive = false
    stop()
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })

  return { refresh, start, stop }
}
