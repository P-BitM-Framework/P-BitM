import { onScopeDispose, readonly, ref, watch } from 'vue'

export function useDelayedIndicator(source, delay = 300) {
  const visible = ref(false)
  let timer = null

  const cancelPendingShow = () => {
    if (timer === null) return
    window.clearTimeout(timer)
    timer = null
  }

  watch(
    source,
    (active) => {
      cancelPendingShow()
      if (!active) {
        visible.value = false
        return
      }

      timer = window.setTimeout(() => {
        visible.value = true
        timer = null
      }, delay)
    },
    { immediate: true, flush: 'sync' }
  )

  onScopeDispose(cancelPendingShow)
  return readonly(visible)
}
