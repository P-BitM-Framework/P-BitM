<template>
  <div class="plugin-editor-view">
    <DelayedContent
      class="plugin-load-gate"
      :loading="loading"
      :show-indicator="showLoading"
    >
    <PluginEditorToolbar
      :plugin-name="plugin?.name"
      :saving="saving"
      :save-disabled="files.length === 0"
      @back="goBack"
      @export="exportPlugin"
      @save="savePlugin"
      @delete="confirmDeletePlugin"
    />

    <div class="editor-container">
      <div class="editor-sidebar">
        <div class="sidebar-content">
          <PluginFileTree
            :files="files"
            :loading="loading"
            :show-loading="showLoading"
            :current-file="currentFile"
            :is-file-modified="isFileModified"
            :get-file-icon="getFileIcon"
            @open-file="openFile"
            @download-file="downloadFile"
            @delete-file="confirmDeleteFile"
            @upload-click="showUploadDialog = true"
            @new-file-click="showNewFileDialog = true"
          />

          <Divider />

          <PluginSettingsPanel
            :plugin="plugin"
            :file-count="files.length"
            @edited="markPluginUnsaved"
          />
        </div>
      </div>

      <PluginTabEditor
        :open-tabs="openTabs"
        :loading="loading"
        :show-loading="showLoading"
        :current-file="currentFile"
        :is-file-modified="isFileModified"
        :get-file-icon="getFileIcon"
        :get-file-language="getFileLanguage"
        :line-count="lineCount"
        :file-size="fileSize"
        @switch-tab="switchTab"
        @close-tab="closeTab"
        @change="markCurrentUnsaved"
        @upload-click="showUploadDialog = true"
        @new-file-click="showNewFileDialog = true"
        @copy="copyCurrentFile"
        @format="formatCode"
      />
    </div>
    </DelayedContent>

    <!-- Upload Files Dialog -->
    <Dialog
      v-model:visible="showUploadDialog"
      modal
      header="Upload Files"
      :style="{ width: '600px' }"
      :draggable="false"
    >
      <div class="upload-container">
        <div
          class="dropzone"
          :class="{ 'dragover': isUploadDragging, 'has-files': uploadedFiles.length > 0 }"
          @drop.prevent="handleUploadDrop"
          @dragover.prevent="isUploadDragging = true"
          @dragleave.prevent="isUploadDragging = false"
          @click="triggerUploadInput"
        >
          <input
            ref="uploadInput"
            type="file"
            accept=".js,.json,.md"
            multiple
            style="display: none"
            @change="handleUploadSelect"
          />

          <div v-if="uploadedFiles.length === 0" class="dropzone-content">
            <i class="pi pi-cloud-upload"></i>
            <h3>Drop files here</h3>
            <p>or click to browse</p>
            <small>Accepted: .js, .json, .md files</small>
          </div>

          <div v-else class="files-preview">
            <div
              v-for="(file, index) in uploadedFiles"
              :key="index"
              class="file-preview-item"
            >
              <Icon :icon="getFileIcon(file.name)" />
              <div class="file-info">
                <strong>{{ file.name }}</strong>
                <span>{{ formatFileSize(file.size) }}</span>
              </div>
              <Button
                icon="pi pi-times"
                text
                rounded
                severity="danger"
                size="small"
                @click.stop="removeUploadedFile(index)"
              />
            </div>
          </div>
        </div>

        <Message v-if="uploadError" severity="error" :closable="false">
          {{ uploadError }}
        </Message>

        <Message severity="info" :closable="false">
          <strong>Note:</strong> Files with the same name will be overwritten.
        </Message>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="closeUploadDialog" />
        <Button
          label="Upload Files"
          icon="pi pi-check"
          :loading="uploading"
          :disabled="uploadedFiles.length === 0"
          @click="confirmUpload"
        />
      </template>
    </Dialog>

    <!-- New File Dialog -->
    <Dialog
      v-model:visible="showNewFileDialog"
      modal
      header="Create New File"
      :style="{ width: '400px' }"
      :draggable="false"
    >
      <div class="field">
        <label for="fileName">File Name <span class="required">*</span></label>
        <InputText
          id="fileName"
          v-model="newFileName"
          placeholder="main.js"
          :invalid="newFileSubmitted && !newFileName"
          autofocus
          @keyup.enter="createFile"
        />
        <small v-if="newFileSubmitted && !newFileName" class="p-error">File name is required</small>
        <small class="text-muted">Include extension (.js, .json, .md)</small>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showNewFileDialog = false" />
        <Button
          label="Create"
          icon="pi pi-check"
          @click="createFile"
        />
      </template>
    </Dialog>

    <!-- Delete File Dialog -->
    <Dialog
      v-model:visible="showDeleteFileDialog"
      modal
      header="Delete File"
      :style="{ width: '400px' }"
      :draggable="false"
    >
      <p>Are you sure you want to delete <strong>{{ fileToDelete?.name }}</strong>?</p>
      <Message severity="warn" :closable="false">
        This action cannot be undone
      </Message>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showDeleteFileDialog = false" />
        <Button
          label="Delete"
          severity="danger"
          icon="pi pi-trash"
          @click="deleteFile"
        />
      </template>
    </Dialog>

    <!-- Delete Plugin Dialog -->
    <Dialog
      v-model:visible="showDeletePluginDialog"
      modal
      header="Delete Plugin"
      :style="{ width: '480px' }"
      :draggable="false"
    >
      <div class="dialog-content">
        <div class="dialog-icon">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <h3>Delete "{{ plugin?.name }}"?</h3>
        <p>This will delete the plugin and all its files permanently.</p>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showDeletePluginDialog = false" />
        <Button
          label="Delete Plugin"
          severity="danger"
          icon="pi pi-trash"
          :loading="deleting"
          @click="deletePlugin"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import { Icon } from '@iconify/vue'
import { usePluginUnsavedState } from '@/composables/usePluginUnsavedState'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DelayedContent from '@/components/default/DelayedContent.vue'
import PluginEditorToolbar from '@/components/plugin/PluginEditorToolbar.vue'
import PluginFileTree from '@/components/plugin/PluginFileTree.vue'
import PluginSettingsPanel from '@/components/plugin/PluginSettingsPanel.vue'
import PluginTabEditor from '@/components/plugin/PluginTabEditor.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const {
  hasUnsavedChanges,
  markUnsaved,
  markPluginUnsaved,
  isFileModified,
  clearUnsaved
} = usePluginUnsavedState()

// State
const saving = ref(false)
const deleting = ref(false)
const uploading = ref(false)
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)

const plugin = ref({
  id: null,
  name: '',
  description: '',
  created_at: null
})

const files = ref([])
const openTabs = ref([])
const currentFile = ref(null)

const showNewFileDialog = ref(false)
const showUploadDialog = ref(false)
const showDeleteFileDialog = ref(false)
const showDeletePluginDialog = ref(false)
const newFileName = ref('')
const newFileSubmitted = ref(false)
const fileToDelete = ref(null)

// Upload state
const isUploadDragging = ref(false)
const uploadedFiles = ref([])
const uploadError = ref('')
const uploadInput = ref(null)

// Computed
const lineCount = computed(() => {
  if (!currentFile.value?.content) return 0
  return currentFile.value.content.split('\n').length
})

const fileSize = computed(() => {
  if (!currentFile.value?.content) return '0 B'
  const bytes = new Blob([currentFile.value.content]).size
  return formatFileSize(bytes)
})

const markCurrentUnsaved = () => markUnsaved(currentFile.value?.name)

// Methods
const fetchPlugin = async () => {
  loading.value = true
  try {
    const data = await backendService.getPlugin(route.params.id)
    plugin.value = data
    files.value = data.files || []
    openTabs.value = []
    currentFile.value = null
    clearUnsaved()

    if (files.value.length > 0) {
      openFile(files.value[0])
    }
  } catch (error) {
    console.error('Failed to fetch plugin:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load plugin', life: 3000 })
    router.push({ name: 'plugins' })
  } finally {
    loading.value = false
  }
}

const openFile = (file) => {
  const existingTab = openTabs.value.find(tab => tab.name === file.name)

  if (existingTab) {
    currentFile.value = existingTab
  } else {
    openTabs.value.push(file)
    currentFile.value = file
  }
}

const switchTab = (tab) => {
  currentFile.value = tab
}

const closeTab = (tab) => {
  const index = openTabs.value.findIndex(t => t.name === tab.name)
  if (index !== -1) {
    openTabs.value.splice(index, 1)

    if (currentFile.value?.name === tab.name) {
      if (openTabs.value.length > 0) {
        const newIndex = index > 0 ? index - 1 : 0
        currentFile.value = openTabs.value[newIndex]
      } else {
        currentFile.value = null
      }
    }
  }
}

const savePlugin = async () => {
  saving.value = true
  try {
    await backendService.updatePlugin(plugin.value.id, {
      name: plugin.value.name,
      description: plugin.value.description,
      files: files.value
    })

    clearUnsaved()

    toast.add({ severity: 'success', summary: 'Saved', detail: 'Plugin saved successfully', life: 2000 })
  } catch (error) {
    console.error('Failed to save plugin:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: error.message || 'Failed to save plugin', life: 3000 })
  } finally {
    saving.value = false
  }
}

const getPluginPathError = (value) => {
  const name = value?.normalize('NFC') || ''
  if (!name || name !== name.trim()) return 'Enter a file path without surrounding spaces'
  if (name.length > 240) return 'File path is too long'
  if (name.startsWith('/') || name.endsWith('/') || name.includes('\\') || name.includes('//')) {
    return 'Use a relative path such as icons/icon.svg'
  }
  if ([...name].some(ch => ch.charCodeAt(0) <= 31)) return 'File path contains invalid characters'

  const parts = name.split('/')
  if (parts.some(part => !part || part === '.' || part === '..' || part.length > 128)) {
    return 'File path contains an unsafe or invalid segment'
  }
  if (/^[A-Za-z]:/.test(parts[0])) return 'Windows drive paths are not allowed'
  return ''
}

const createFile = () => {
  newFileSubmitted.value = true

  if (!newFileName.value) {
    return
  }

  const pathError = getPluginPathError(newFileName.value)
  if (pathError) {
    toast.add({ severity: 'warn', summary: 'Invalid file path', detail: pathError, life: 3500 })
    return
  }

  const normalizedName = newFileName.value.normalize('NFC')
  if (files.value.some(f => f.name === normalizedName)) {
    toast.add({ severity: 'warn', summary: 'Warning', detail: 'File already exists', life: 3000 })
    return
  }

  const newFile = {
    name: normalizedName,
    content: getFileTemplate(normalizedName)
  }

  files.value.push(newFile)
  openFile(newFile)
  markUnsaved(newFile.name)

  showNewFileDialog.value = false
  newFileName.value = ''
  newFileSubmitted.value = false

  toast.add({ severity: 'success', summary: 'Created', detail: `File ${newFile.name} created`, life: 2000 })
}

const copyCurrentFile = async () => {
  try {
    await navigator.clipboard.writeText(currentFile.value?.content || '')
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: `${currentFile.value.name} copied to clipboard`,
      life: 2000
    })
  } catch (_error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy to clipboard', life: 3000 })
  }
}

// Upload methods
const triggerUploadInput = () => {
  if (uploadedFiles.value.length === 0) {
    uploadInput.value?.click()
  }
}

const handleUploadSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  processUploadFiles(selectedFiles)
}

const handleUploadDrop = (event) => {
  isUploadDragging.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  processUploadFiles(droppedFiles)
}

const processUploadFiles = (filesList) => {
  uploadError.value = ''
  const validExtensions = ['.js', '.json', '.md']

  const validFiles = filesList.filter(file => {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    return validExtensions.includes(ext)
  })

  if (validFiles.length !== filesList.length) {
    uploadError.value = 'Some files were skipped. Only .js, .json, and .md files are allowed.'
  }

  uploadedFiles.value = [...uploadedFiles.value, ...validFiles]
}

const removeUploadedFile = (index) => {
  uploadedFiles.value.splice(index, 1)
}

const confirmUpload = async () => {
  if (uploadedFiles.value.length === 0) return

  uploading.value = true

  try {
    const filePromises = uploadedFiles.value.map(file => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => {
          resolve({ name: file.name, content: e.target.result })
        }
        reader.onerror = reject
        reader.readAsText(file)
      })
    })

    const uploadedFilesData = await Promise.all(filePromises)

    uploadedFilesData.forEach(uploadedFile => {
      const existingIndex = files.value.findIndex(f => f.name === uploadedFile.name)
      if (existingIndex !== -1) {
        Object.assign(files.value[existingIndex], uploadedFile)
      } else {
        files.value.push(uploadedFile)
      }

      markUnsaved(uploadedFile.name)
    })

    toast.add({
      severity: 'success',
      summary: 'Uploaded',
      detail: `${uploadedFilesData.length} file(s) uploaded successfully`,
      life: 2000
    })

    closeUploadDialog()

    if (uploadedFilesData.length > 0 && !currentFile.value) {
      const firstUploadedFile = files.value.find(file => file.name === uploadedFilesData[0].name)
      if (firstUploadedFile) openFile(firstUploadedFile)
    }
  } catch (error) {
    console.error('Failed to upload files:', error)
    uploadError.value = 'Failed to read files'
  } finally {
    uploading.value = false
  }
}

const closeUploadDialog = () => {
  showUploadDialog.value = false
  uploadedFiles.value = []
  uploadError.value = ''
  if (uploadInput.value) {
    uploadInput.value.value = ''
  }
}

const confirmDeleteFile = (file) => {
  fileToDelete.value = file
  showDeleteFileDialog.value = true
}

const deleteFile = () => {
  if (!fileToDelete.value) return

  const index = files.value.findIndex(f => f.name === fileToDelete.value.name)
  if (index !== -1) {
    const deletedFileName = fileToDelete.value.name
    files.value.splice(index, 1)

    const tabIndex = openTabs.value.findIndex(t => t.name === deletedFileName)
    if (tabIndex !== -1) {
      openTabs.value.splice(tabIndex, 1)

      if (currentFile.value?.name === deletedFileName) {
        if (openTabs.value.length > 0) {
          const nextIndex = Math.min(tabIndex, openTabs.value.length - 1)
          currentFile.value = openTabs.value[nextIndex]
        } else {
          currentFile.value = null
        }
      }
    }

    clearUnsaved(deletedFileName)
    markPluginUnsaved()

    toast.add({ severity: 'success', summary: 'Deleted', detail: `File ${deletedFileName} deleted`, life: 2000 })
  }

  showDeleteFileDialog.value = false
  fileToDelete.value = null
}

const downloadFile = (file) => {
  const blob = new Blob([file.content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = file.name
  a.click()
  URL.revokeObjectURL(url)
}

const exportPlugin = async () => {
  try {
    await backendService.exportPlugin(plugin.value.id)
    toast.add({ severity: 'success', summary: 'Exported', detail: 'Plugin exported successfully', life: 2000 })
  } catch (error) {
    console.error('Failed to export plugin:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to export plugin', life: 3000 })
  }
}

const confirmDeletePlugin = () => {
  showDeletePluginDialog.value = true
}

const deletePlugin = async () => {
  deleting.value = true
  try {
    await backendService.deletePlugin(plugin.value.id)
    toast.add({ severity: 'success', summary: 'Deleted', detail: 'Plugin deleted successfully', life: 3000 })
    router.push({ name: 'plugins' })
  } catch (error) {
    console.error('Failed to delete plugin:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete plugin', life: 3000 })
  } finally {
    deleting.value = false
  }
}

const formatCode = () => {
  if (!currentFile.value) return

  try {
    const lang = getFileLanguage(currentFile.value.name).toLowerCase()
    if (lang === 'json') {
      const parsed = JSON.parse(currentFile.value.content)
      currentFile.value.content = JSON.stringify(parsed, null, 2)
      markCurrentUnsaved()
      toast.add({ severity: 'success', summary: 'Formatted', detail: 'Code formatted successfully', life: 2000 })
    }
  } catch (_error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to format code', life: 3000 })
  }
}

const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const icons = {
    js: 'vscode-icons:file-type-js',
    json: 'vscode-icons:file-type-json',
    md: 'vscode-icons:file-type-markdown',
    html: 'vscode-icons:file-type-html',
    css: 'vscode-icons:file-type-css2',
    default: 'vscode-icons:file-type-unknown'
  }
  return icons[ext] || 'vscode-icons:file-type-unknown'
}

const getFileLanguage = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const languages = {
    js: 'JavaScript',
    mjs: 'JavaScript',
    cjs: 'JavaScript',
    jsx: 'JavaScript',
    ts: 'TypeScript',
    tsx: 'TypeScript',
    json: 'JSON',
    md: 'Markdown',
    html: 'HTML',
    htm: 'HTML',
    css: 'CSS',
    scss: 'SCSS',
    py: 'Python',
    sh: 'Shell',
    bash: 'Shell',
    yaml: 'YAML',
    yml: 'YAML',
    xml: 'XML'
  }
  return languages[ext] || 'plaintext'
}

const getFileTemplate = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const templates = {
    js: '// JavaScript plugin file\n\n(function() {\n  console.log("Plugin loaded");\n})();\n',
    json: '{\n  "name": "config",\n  "version": "1.0.0"\n}\n',
    md: '# Plugin Documentation\n\n## Description\n\nAdd your documentation here.\n'
  }
  return templates[ext] || ''
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const goBack = () => {
  if (hasUnsavedChanges.value) {
    if (!confirm('You have unsaved changes. Discard them?')) {
      return
    }
  }
  router.push({ name: 'plugins' })
}

const handleKeyboard = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    savePlugin()
  }
}

onMounted(() => {
  fetchPlugin()
  document.addEventListener('keydown', handleKeyboard)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeyboard)
})
</script>

<style scoped>
.plugin-editor-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--color-background);
}

.plugin-load-gate {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.plugin-load-gate :deep(.delayed-content-body) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.editor-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor-sidebar {
  width: 300px;
  background-color: var(--color-background-soft);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.upload-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.dropzone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: var(--transition-interactive);
  background-color: var(--color-background-soft);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dropzone:hover {
  border-color: var(--primary-color);
  background-color: var(--color-background-mute);
}

.dropzone.dragover {
  border-color: var(--primary-color);
  background-color: var(--primary-subtle);
  transform: scale(1.02);
}

.dropzone.has-files {
  cursor: default;
  padding: 1rem;
  align-items: flex-start;
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: var(--color-text-mute);
}

.dropzone-content i {
  font-size: 4rem;
  color: var(--primary-color);
  opacity: 0.5;
}

.dropzone-content h3 {
  margin: 0;
  font-size: 1.125rem;
  color: var(--color-heading);
}

.dropzone-content p {
  margin: 0;
  font-size: 0.875rem;
}

.dropzone-content small {
  color: var(--color-text-mute);
  font-size: 0.813rem;
}

.files-preview {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.file-preview-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.file-preview-item i {
  font-size: 1.5rem;
  color: var(--primary-color);
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-info strong {
  color: var(--color-heading);
  font-size: 0.875rem;
}

.file-info span {
  color: var(--color-text-mute);
  font-size: 0.813rem;
}

.dialog-content {
  padding: 1rem;
  text-align: center;
}

.dialog-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--danger-subtle);
  border-radius: 50%;
}

.dialog-icon i {
  font-size: 2rem;
  color: var(--danger);
}

.dialog-content h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
}

.dialog-content p {
  margin: 0 0 1rem 0;
  color: var(--color-text-mute);
  line-height: 1.6;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.813rem;
  color: var(--color-heading);
}

.p-error {
  color: var(--red-500);
  font-size: 0.85rem;
}

.required {
  color: var(--red-500);
}

.text-muted {
  color: var(--color-text-mute);
  font-size: 0.813rem;
}

@media (max-width: 768px) {
  .editor-sidebar {
    width: 250px;
  }
}
</style>
