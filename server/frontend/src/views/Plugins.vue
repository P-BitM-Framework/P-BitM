<template>
  <div class="plugins-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader title="Browser Extensions" subtitle="Manage browser automation extensions">
      <template #actions>
        <Button
          label="Import"
          icon="pi pi-upload"
          severity="secondary"
          outlined
          @click="showImportDialog = true"
        />
        <Button
          label="New Plugin"
          icon="pi pi-plus"
          @click="openCreateDialog"
        />
      </template>
    </PageHeader>

    <!-- Table Card -->
    <Card class="plugins-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-title app-section-title">
            <Icon icon="mdi:firefox" width="24px"/>
            Available Plugins
            <span class="count-badge">{{ plugins.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search plugins..."
                class="search-input"
              />
            </IconField>

            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              @click="fetchPlugins"
              :loading="showLoading"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="plugins"
          :loading="showLoading"
          :filters="filters"
          :clickableRows="true"
          @row-click="openEditor($event.data)"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          class="data-table data-table--interactive"
        >
          <Column field="name" header="Plugin Name" sortable style="min-width: 100px">
            <template #body="{ data }">
              <div class="plugin-cell">
                <div class="plugin-icon">
                  <Icon icon="mdi:firefox" width="28px"/>
                </div>
                <div class="plugin-details">
                  <strong>{{ data.name }}</strong>
                  <!-- <span class="plugin-description">{{ data.description || 'No description' }}</span> -->
                </div>
              </div>
            </template>
          </Column>

          <Column field="description" header="Description" sortable>
            <template #body="{ data }">
              <span class="description-text">{{ data.description || '-' }}</span>
            </template>
          </Column>

          <Column field="files" header="Files" sortable style="width: 120px">
            <template #body="{ data }">
              <span class="file-count">
                <i class="pi pi-file"></i>
                {{ data.files?.length || 0 }}
              </span>
            </template>
          </Column>

          <Column field="created_at" header="Created" sortable style="width: 150px">
            <template #body="{ data }">
              <span class="time-ago">
                <i class="pi pi-calendar"></i>
                {{ formatDateLocal(data.created_at) }}
              </span>
            </template>
          </Column>

          <Column header="Actions" style="width: 140px" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Edit'"
                  @click.stop="openEditor(data)"
                />
                <Button
                  icon="pi pi-download"
                  severity="info"
                  text
                  rounded
                  v-tooltip.top="'Export'"
                  @click.stop="exportPlugin(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  v-tooltip.top="'Delete'"
                  @click.stop="confirmDelete(data)"
                />
              </div>
            </template>
          </Column>

          <template #empty>
            <div class="empty-state">
              <i class="pi pi-inbox"></i>
              <p>No plugins found. Create your first plugin.</p>
              <Button
                label="Create Plugin"
                icon="pi pi-plus"
                @click="openCreateDialog"
                size="small"
                class="mt-2"
              />
            </div>
          </template>
        </DataTable>
      </template>
    </Card>
    </DelayedContent>

    <!-- Create Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      modal
      header="Create New Plugin"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="create-form">
        <div class="field">
          <label for="pluginName">Plugin Name <span class="required">*</span></label>
          <InputText
            id="pluginName"
            v-model="newPlugin.name"
            placeholder="Keylogger"
            :invalid="createSubmitted && !newPlugin.name"
            autofocus
          />
          <small v-if="createSubmitted && !newPlugin.name" class="p-error">Name is required</small>
        </div>

        <div class="field">
          <label for="pluginDesc">Description</label>
          <Textarea
            id="pluginDesc"
            v-model="newPlugin.description"
            rows="3"
            placeholder="Captures keyboard input..."
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showCreateDialog = false" />
        <Button
          label="Create & Edit"
          icon="pi pi-check"
          :loading="creating"
          @click="createPlugin"
        />
      </template>
    </Dialog>

    <!-- Import Dialog -->
    <Dialog
      v-model:visible="showImportDialog"
      modal
      header="Import Plugin"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="import-container">
        <div
          class="dropzone"
          :class="{ 'dragover': isDragging, 'has-file': selectedFile }"
          @drop.prevent="handleDrop"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".zip"
            style="display: none"
            @change="handleFileSelect"
          />

          <div v-if="!selectedFile" class="dropzone-content">
            <i class="pi pi-cloud-upload"></i>
            <h3>Drop plugin ZIP here</h3>
            <p>or click to browse</p>
            <small>Only .zip files are supported</small>
          </div>

          <div v-else class="file-preview">
            <i class="pi pi-file-export"></i>
            <div class="file-info">
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ formatFileSize(selectedFile.size) }}</span>
            </div>
            <Button
              icon="pi pi-times"
              text
              rounded
              severity="danger"
              @click.stop="clearFile"
            />
          </div>
        </div>

        <Message v-if="importError" severity="error" :closable="false">
          {{ importError }}
        </Message>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="closeImportDialog" />
        <Button
          label="Import Plugin"
          icon="pi pi-check"
          :loading="importing"
          :disabled="!selectedFile"
          @click="importPlugin"
        />
      </template>
    </Dialog>

    <!-- Delete Dialog -->
    <Dialog
      v-model:visible="showDeleteDialog"
      modal
      header="Delete Plugin"
      :style="{ width: '480px' }"
      :draggable="false"
    >
      <div class="dialog-content">
        <div class="dialog-icon">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <h3>Delete "{{ pluginToDelete?.name }}"?</h3>
        <p>This will delete all plugin files and cannot be undone.</p>
        <Message severity="warn" :closable="false" class="mt-3">
          Campaigns using this plugin will no longer have it available.
        </Message>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showDeleteDialog = false" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import { backendService } from '@/services/backend'
import { Icon } from '@iconify/vue'
import { formatDateLocal } from '@/utils/utils'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const router = useRouter()
const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const creating = ref(false)
const deleting = ref(false)
const importing = ref(false)
const createSubmitted = ref(false)
const plugins = ref([])
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showImportDialog = ref(false)
const pluginToDelete = ref(null)

// Import state
const isDragging = ref(false)
const selectedFile = ref(null)
const importError = ref('')
const fileInput = ref(null)

const newPlugin = ref({
  name: '',
  description: ''
})

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Methods
const fetchPlugins = async () => {
  loading.value = true
  try {
    const data = await backendService.getPlugins()
    plugins.value = data.plugins || []
  } catch (error) {
    console.error('Failed to fetch plugins:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load plugins',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  newPlugin.value = {
    name: '',
    description: ''
  }
  createSubmitted.value = false
  showCreateDialog.value = true
}

const createPlugin = async () => {
  createSubmitted.value = true

  if (!newPlugin.value.name) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Plugin name is required',
      life: 3000
    })
    return
  }

  creating.value = true
  try {
    const response = await backendService.createPlugin(newPlugin.value)

    toast.add({
      severity: 'success',
      summary: 'Created',
      detail: 'Plugin created successfully',
      life: 3000
    })

    showCreateDialog.value = false
    router.push({ name: 'plugin-editor', params: { id: response.id } })
  } catch (error) {
    console.error('Failed to create plugin:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to create plugin',
      life: 3000
    })
  } finally {
    creating.value = false
  }
}

const openEditor = (plugin) => {
  router.push({ name: 'plugin-editor', params: { id: plugin.id } })
}

const exportPlugin = async (plugin) => {
  try {
    toast.add({
      severity: 'info',
      summary: 'Exporting',
      detail: `Exporting plugin "${plugin.name}"...`,
      life: 2000
    })

    await backendService.exportPlugin(plugin.id)

    toast.add({
      severity: 'success',
      summary: 'Exported',
      detail: `Plugin "${plugin.name}" exported successfully`,
      life: 3000
    })
  } catch (error) {
    console.error('Failed to export plugin:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to export plugin',
      life: 3000
    })
  }
}

const confirmDelete = (plugin) => {
  pluginToDelete.value = plugin
  showDeleteDialog.value = true
}

const deletePlugin = async () => {
  if (!pluginToDelete.value) return

  deleting.value = true
  try {
    await backendService.deletePlugin(pluginToDelete.value.id)

    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: `Plugin "${pluginToDelete.value.name}" deleted successfully`,
      life: 3000
    })

    showDeleteDialog.value = false
    pluginToDelete.value = null
    await fetchPlugins()
  } catch (error) {
    console.error('Failed to delete plugin:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete plugin',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

// Import methods
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
    importError.value = ''
  } else {
    importError.value = 'Only ZIP files are supported'
  }
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]

  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
    importError.value = ''
  } else {
    importError.value = 'Only ZIP files are supported'
  }
}

const clearFile = () => {
  selectedFile.value = null
  importError.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const importPlugin = async () => {
  if (!selectedFile.value) return

  importing.value = true
  importError.value = ''

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    await backendService.importPlugin(formData)

    toast.add({
      severity: 'success',
      summary: 'Imported',
      detail: 'Plugin imported successfully',
      life: 3000
    })

    closeImportDialog()
    await fetchPlugins()
  } catch (error) {
    console.error('Failed to import plugin:', error)
    importError.value = error.message || 'Failed to import plugin'
  } finally {
    importing.value = false
  }
}

const closeImportDialog = () => {
  showImportDialog.value = false
  clearFile()
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(() => {
  fetchPlugins()
})
</script>

<style scoped>
/* Base Layout */
.plugins-view {
  padding: var(--page-padding);
  max-width: var(--content-max-width);
  margin: 0 auto;
  min-height: 100vh;
}

/* Table Card */
.plugins-table-card :deep(.p-card-body) {
  padding: 0;
}

.plugins-table-card :deep(.p-card-content) {
  padding: 0;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.section-title i {
  color: var(--color-text-mute);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem 0.625rem;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-mute);
}

.table-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.search-input {
  width: 250px;
}

/* Plugin Cell */
.plugin-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.plugin-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    border-radius: var(--radius-sm);
    color: var(--color-text);
    flex-shrink: 0;
    transition: var(--transition-interactive);
}

.data-table :deep(tr:hover) .plugin-icon {
    background: transparent;
    transform: none;
}

.plugin-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.plugin-description {
  font-size: 0.813rem;
  color: var(--color-text-mute);
}

/* Description Text */
.description-text {
  font-size: 0.875rem;
  color: var(--color-text);
}

/* File Count */
.file-count {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: var(--color-text-mute);
}

.file-count i {
  font-size: 0.75rem;
}

/* Time Ago */
.time-ago {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: var(--color-text-mute);
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  justify-content: flex-end;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 2rem;
  color: var(--color-text-mute);
}

.empty-state i {
  font-size: 3rem;
  opacity: 0.5;
}

/* Forms */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--color-heading);
}

.p-error {
  color: var(--red-500);
  font-size: 0.85rem;
}

.required {
  color: var(--red-500);
}

/* Import Container */
.import-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

/* Dropzone */
.dropzone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: var(--transition-interactive);
  background-color: var(--color-background-soft);
}

.dropzone:hover {
  border-color: var(--p-primary-color);
  background-color: var(--color-background-mute);
}

.dropzone.dragover {
  border-color: var(--p-primary-color);
  background-color: var(--primary-subtle);
  transform: scale(1.02);
}

.dropzone.has-file {
  border-style: solid;
  border-color: var(--p-primary-color);
  background-color: var(--color-background);
  padding: 1.5rem;
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
  color: var(--p-primary-color);
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

/* File Preview */
.file-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.file-preview i {
  font-size: 2.5rem;
  color: var(--p-primary-color);
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-align: left;
}

.file-info strong {
  color: var(--color-heading);
  font-size: 0.938rem;
}

.file-info span {
  color: var(--color-text-mute);
  font-size: 0.813rem;
}

/* Delete Dialog */
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

/* Responsive */
@media (max-width: 768px) {
  .plugins-view {
    padding: 1rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .table-header {
    flex-direction: column;
    align-items: stretch;
  }

  .table-controls {
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }
}
</style>
