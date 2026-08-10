import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

/**
 * Tracks which plugin files have unsaved edits and warns before the
 * browser tab closes while changes are pending.
 */
export function usePluginUnsavedState() {
  const modifiedFiles = ref(new Set())
  const pluginModified = ref(false)
  const hasUnsavedChanges = computed(() => pluginModified.value || modifiedFiles.value.size > 0)

  function markUnsaved(fileName) {
    if (fileName) modifiedFiles.value.add(fileName)
  }

  function markPluginUnsaved() {
    pluginModified.value = true
  }

  function isFileModified(fileName) {
    return modifiedFiles.value.has(fileName)
  }

  function clearUnsaved(fileName) {
    if (fileName) modifiedFiles.value.delete(fileName)
    else {
      modifiedFiles.value.clear()
      pluginModified.value = false
    }
  }

  function handleBeforeUnload(e) {
    if (hasUnsavedChanges.value) {
      e.preventDefault()
      e.returnValue = ''
    }
  }

  onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', handleBeforeUnload))

  return {
    hasUnsavedChanges,
    markUnsaved,
    markPluginUnsaved,
    isFileModified,
    clearUnsaved
  }
}
