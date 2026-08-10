import { computed, ref } from 'vue'
import { backendService } from '@/services/backend'

export function useTargetImport({ getListId, refresh, saving, toast, showImportDialog, showBulkDialog }) {
  const importing = ref(false)
  const fileUploader = ref(null)
  const bulkText = ref('')
  const csvData = ref([])

  const csvPreview = computed(() => csvData.value.slice(0, 5))

  const parseBulkLine = (line) => {
    const parts = line.split(',').map((part) => part.trim())
    const email = parts[0] || ''
    let first_name = ''
    let last_name = ''

    if (parts[1]) {
      const nameParts = parts[1].trim().split(' ')
      first_name = nameParts[0] || ''
      last_name = nameParts.slice(1).join(' ') || ''
    }

    return {
      email,
      first_name,
      last_name,
      position: parts[2] || '',
      department: parts[3] || ''
    }
  }

  const bulkPreview = computed(() => {
    if (!bulkText.value.trim()) return []
    const lines = bulkText.value.split('\n').filter((line) => line.trim())
    return lines.slice(0, 5).map((line) => parseBulkLine(line))
  })

  const onFileSelect = (event) => {
    const file = event.files[0]
    const reader = new FileReader()

    reader.onload = (loadEvent) => {
      const text = loadEvent.target.result
      const lines = text.split('\n').filter((line) => line.trim())
      const startIndex = lines[0].toLowerCase().includes('email') ? 1 : 0

      csvData.value = lines.slice(startIndex).map((line) => {
        const values = line.match(/(".*?"|[^,]+)(?=\s*,|\s*$)/g) || []
        const cleanValues = values.map((value) => value.replace(/^"|"$/g, '').trim())
        return {
          email: cleanValues[0] || '',
          first_name: cleanValues[1] || '',
          last_name: cleanValues[2] || '',
          position: cleanValues[3] || '',
          department: cleanValues[4] || ''
        }
      }).filter((row) => row.email)
    }

    reader.readAsText(file)
  }

  const importCSV = async () => {
    if (!csvData.value.length) {
      toast.add({ severity: 'warn', summary: 'Warning', detail: 'No valid targets found in CSV', life: 3000 })
      return
    }

    importing.value = true
    try {
      const result = await backendService.bulkAddTargets(getListId(), csvData.value)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `${result.added || csvData.value.length} targets imported successfully`,
        life: 3000
      })
      showImportDialog.value = false
      await refresh()
    } catch (error) {
      console.error('Failed to import targets:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: error.message || 'Failed to import targets', life: 3000 })
    } finally {
      importing.value = false
    }
  }

  const resetImportForm = () => {
    csvData.value = []
    fileUploader.value?.clear()
  }

  const bulkAddTargets = async () => {
    const lines = bulkText.value.split('\n').filter((line) => line.trim())
    if (!lines.length) {
      toast.add({ severity: 'warn', summary: 'Warning', detail: 'Please enter at least one target', life: 3000 })
      return
    }

    const targetsToAdd = lines.map((line) => parseBulkLine(line)).filter((target) => target.email)
    if (!targetsToAdd.length) {
      toast.add({ severity: 'warn', summary: 'Warning', detail: 'No valid email addresses found', life: 3000 })
      return
    }

    saving.value = true
    try {
      const result = await backendService.bulkAddTargets(getListId(), targetsToAdd)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `${result.added || targetsToAdd.length} targets added successfully`,
        life: 3000
      })
      showBulkDialog.value = false
      await refresh()
    } catch (error) {
      console.error('Failed to add targets:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: error.message || 'Failed to add targets', life: 3000 })
    } finally {
      saving.value = false
    }
  }

  const resetBulkForm = () => {
    bulkText.value = ''
  }

  return {
    bulkAddTargets,
    bulkPreview,
    bulkText,
    csvData,
    csvPreview,
    fileUploader,
    importing,
    importCSV,
    onFileSelect,
    resetBulkForm,
    resetImportForm
  }
}
