<template>
  <div class="landing-pages-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader title="Landing Pages" subtitle="Create and manage campaign landing pages">
      <template #actions>
        <Button
          label="New Landing Page"
          icon="pi pi-plus"
          @click="openCreateDialog"
        />
      </template>
    </PageHeader>

    <!-- Table Card -->
    <Card class="landing-pages-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-title app-section-title">
            <i class="pi pi-globe"></i>
            Landing Pages
            <span class="count-badge">{{ landingPages.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search landing pages..."
                class="search-input"
              />
            </IconField>

            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              @click="fetchLandingPages"
              :loading="showLoading"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="landingPages"
          :loading="showLoading"
          :filters="filters"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          clickableRows
          @row-click="openEditDialog($event.data)"
          class="data-table data-table--interactive"
        >
          <Column field="name" header="Landing Page Name" sortable style="min-width: 250px">
            <template #body="{ data }">
              <div class="page-cell">
                <div class="page-icon">
                  <i class="pi pi-globe"></i>
                </div>
                <div class="page-details">
                  <strong>{{ data.name }}</strong>
                  <span class="page-description">{{ data.description || 'No description' }}</span>
                </div>
              </div>
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

          <Column header="Actions" style="width: 200px" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-eye"
                  severity="info"
                  text
                  rounded
                  v-tooltip.top="'Preview'"
                  @click.stop="previewLandingPage(data)"
                />
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Edit'"
                  @click.stop="openEditDialog(data)"
                />
                <Button
                  icon="pi pi-download"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Export'"
                  @click.stop="exportLandingPage(data.id)"
                />
                <Button
                  icon="pi pi-copy"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Clone'"
                  @click.stop="openCloneDialog(data)"
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
              <p>No landing pages found. Create your first landing page.</p>
              <Button
                label="Create Landing Page"
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

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showEditDialog"
      modal
      :header="dialogMode === 'edit' ? 'Edit Landing Page' : 'Create Landing Page'"
      class="app-text-editor-dialog landing-page-editor-dialog"
      :style="{ width: '95vw', maxWidth: '1800px' }"
      :draggable="false"
      @hide="onDialogHide"
    >
      <div class="dialog-layout">
        <!-- Left Sidebar: Settings -->
        <div class="settings-sidebar">
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-cog"></i>
              Settings
            </h3>

            <div class="field">
              <label for="pageName">Name <span class="required">*</span></label>
              <InputText
                id="pageName"
                v-model="landingPageForm.name"
                placeholder="Login Page"
                :invalid="submitted && !landingPageForm.name"
              />
              <small v-if="submitted && !landingPageForm.name" class="p-error">Name is required</small>
            </div>

            <div class="field">
              <label for="description">Description</label>
              <Textarea
                id="description"
                v-model="landingPageForm.description"
                rows="3"
                placeholder="Brief description..."
              />
            </div>
          </div>

          <Divider />

          <!-- Template Variables -->
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-hashtag"></i>
              Variables
            </h3>

            <p class="section-description">
              Click to copy variable to clipboard
            </p>

            <div class="variables-grid">
              <Tag
                v-for="variable in templateVariables"
                :key="variable"
                :value="variable"
                severity="secondary"
                class="variable-tag"
                @click="copyVariable(variable)"
              />
            </div>
          </div>

          <Divider />

          <!-- Quick Actions -->
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-bolt"></i>
              Quick Actions
            </h3>

            <div class="action-buttons-grid">
              <Button
                label="Use Template"
                icon="pi pi-file-import"
                severity="secondary"
                outlined
                @click="insertTemplate"
                class="action-btn"
              />
              <Button
                label="Import HTML"
                icon="pi pi-upload"
                severity="secondary"
                outlined
                @click="triggerImportInput"
                class="action-btn"
              />
              <Button
                label="Preview"
                icon="pi pi-eye"
                severity="info"
                @click="previewCurrentPage"
                class="action-btn"
              />
            </div>

            <!-- Hidden file input -->
            <input
              ref="importInput"
              type="file"
              accept=".html"
              style="display: none"
              @change="handleImportSelect"
            />
          </div>

          <Divider />

          <!-- Info -->
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-info-circle"></i>
              Tips
            </h3>

            <div class="tips-list">
              <div class="tip-item">
                <i class="pi pi-check-circle"></i>
                <span>Use variables like <code v-pre>{{first_name}}</code></span>
              </div>
              <div class="tip-item">
                <i class="pi pi-check-circle"></i>
                <span>Include inline CSS & JavaScript</span>
              </div>
              <div class="tip-item">
                <i class="pi pi-check-circle"></i>
                <span>Test with Preview before saving</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Side: Code Editor -->
        <div class="editor-container">
          <CodeCard
            v-model="landingPageForm.content"
            title="HTML Content"
            icon="pi pi-globe"
            language="html"
            height="100%"
            :required="true"
            :error="submitted && !landingPageForm.content ? 'HTML content is required' : ''"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer-actions">
          <Button
            label="Cancel"
            severity="secondary"
            text
            @click="showEditDialog = false"
          />
          <Button
            label="Preview"
            severity="info"
            icon="pi pi-eye"
            outlined
            @click="previewCurrentPage"
          />
          <Button
            :label="dialogMode === 'edit' ? 'Update' : 'Create'"
            icon="pi pi-check"
            :loading="saving"
            @click="saveLandingPage"
          />
        </div>
      </template>
    </Dialog>

    <!-- Preview Dialog -->
    <Dialog
      v-model:visible="showPreviewDialog"
      modal
      header="Landing Page Preview"
      :style="{ width: '90vw', maxWidth: '1400px', height: '90vh' }"
      :draggable="false"
    >
      <div class="preview-container">
        <div class="preview-header">
          <div class="preview-info">
            <strong>{{ selectedPage?.name }}</strong>
            <span v-if="selectedPage?.description">{{ selectedPage.description }}</span>
          </div>
          <Button
            label="Open in New Tab"
            icon="pi pi-external-link"
            text
            size="small"
            @click="openInNewTab"
          />
        </div>

        <div class="preview-frame">
          <iframe
            :srcdoc="selectedPage?.content"
            sandbox="allow-scripts allow-forms"
            class="preview-iframe"
          ></iframe>
        </div>
      </div>

      <template #footer>
        <Button label="Close" severity="secondary" text @click="showPreviewDialog = false" />
        <Button
          v-if="selectedPage?.id"
          label="Edit"
          icon="pi pi-pencil"
          @click="editFromPreview"
        />
      </template>
    </Dialog>

    <!-- Clone Dialog -->
    <Dialog
      v-model:visible="showCloneDialog"
      modal
      header="Clone Landing Page"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="field">
        <label for="cloneName">New Landing Page Name <span class="required">*</span></label>
        <InputText
          id="cloneName"
          v-model="cloneName"
          :placeholder="`${pageToClone?.name} (Copy)`"
          :invalid="cloneSubmitted && !cloneName"
          autofocus
        />
        <small v-if="cloneSubmitted && !cloneName" class="p-error">Name is required</small>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showCloneDialog = false" />
        <Button
          label="Clone"
          icon="pi pi-copy"
          :loading="cloning"
          @click="cloneLandingPage"
        />
      </template>
    </Dialog>

    <DeleteResourceDialog
      v-model:visible="showDeleteDialog"
      header="Delete Landing Page"
      :subject="pageToDelete?.name"
      :loading="deleting"
      @confirm="deleteLandingPage"
    >
      <p>This action cannot be undone</p>
      <Message severity="warn" :closable="false" class="mt-3">
        Campaigns using this landing page may be affected.
      </Message>
    </DeleteResourceDialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import { backendService } from '@/services/backend'
import CodeCard from '@/components/default/CodeCard.vue'
import { formatDateLocal } from '@/utils/utils'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DeleteResourceDialog from '@/components/default/DeleteResourceDialog.vue'
import { DEFAULT_LANDING_PAGE_TEMPLATE } from '@/constants/landingPageDefaults'

const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const deleting = ref(false)
const cloning = ref(false)
const submitted = ref(false)
const cloneSubmitted = ref(false)

const landingPages = ref([])
const showEditDialog = ref(false)
const showPreviewDialog = ref(false)
const showCloneDialog = ref(false)
const showDeleteDialog = ref(false)
const dialogMode = ref('create')

const selectedPage = ref(null)
const pageToDelete = ref(null)
const pageToClone = ref(null)
const cloneName = ref('')

const importInput = ref(null)

const landingPageForm = ref({
  id: null,
  name: '',
  description: '',
  content: ''
})

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Template Variables (simple string replacement)
const templateVariables = [
  '{{target_url}}',
  '{{first_name}}',
  '{{last_name}}',
  '{{email}}',
  '{{company}}',
  '{{position}}'
]

// Methods
const fetchLandingPages = async () => {
  loading.value = true
  try {
    const data = await backendService.getLandingPages()
    landingPages.value = data.landing_pages || []
  } catch (error) {
    console.error('Failed to fetch landing pages:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load landing pages',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  resetForm()
  landingPageForm.value.content = DEFAULT_LANDING_PAGE_TEMPLATE
  showEditDialog.value = true
}

const openEditDialog = (page) => {
  dialogMode.value = 'edit'
  landingPageForm.value = { ...page }
  showEditDialog.value = true
}

const saveLandingPage = async () => {
  submitted.value = true

  if (!landingPageForm.value.name || !landingPageForm.value.content) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Please fill all required fields',
      life: 3000
    })
    return
  }

  saving.value = true
  try {
    if (dialogMode.value === 'edit') {
      await backendService.updateLandingPage(landingPageForm.value.id, landingPageForm.value)
      toast.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Landing page updated successfully',
        life: 3000
      })
    } else {
      await backendService.createLandingPage(landingPageForm.value)
      toast.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Landing page created successfully',
        life: 3000
      })
    }

    showEditDialog.value = false
    await fetchLandingPages()
  } catch (error) {
    console.error('Failed to save landing page:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save landing page',
      life: 3000
    })
  } finally {
    saving.value = false
    submitted.value = false
  }
}

const copyVariable = async (variable) => {
  try {
    await navigator.clipboard.writeText(variable)
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: `${variable} copied to clipboard`,
      life: 2000
    })
  } catch (error) {
    console.error('Failed to copy:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy to clipboard',
      life: 3000
    })
  }
}

const previewLandingPage = (page) => {
  selectedPage.value = page
  showPreviewDialog.value = true
}

const previewCurrentPage = () => {
  if (!landingPageForm.value.content) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'No content to preview',
      life: 2000
    })
    return
  }

  selectedPage.value = { ...landingPageForm.value }
  showPreviewDialog.value = true
}

const editFromPreview = () => {
  showPreviewDialog.value = false
  if (selectedPage.value.id) {
    openEditDialog(selectedPage.value)
  }
}

const openInNewTab = () => {
  if (!selectedPage.value?.content) return

  const newWindow = window.open('', '_blank')
  if (newWindow) {
    newWindow.opener = null
    newWindow.document.title = selectedPage.value.name || 'Landing Page Preview'
    newWindow.document.body.style.margin = '0'
    newWindow.document.body.style.width = '100vw'
    newWindow.document.body.style.height = '100vh'

    const previewFrame = newWindow.document.createElement('iframe')
    previewFrame.setAttribute('sandbox', 'allow-scripts allow-forms')
    previewFrame.setAttribute('title', 'Sandboxed landing page preview')
    previewFrame.style.border = '0'
    previewFrame.style.width = '100%'
    previewFrame.style.height = '100%'
    previewFrame.srcdoc = selectedPage.value.content
    newWindow.document.body.appendChild(previewFrame)
  } else {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Please allow popups',
      life: 3000
    })
  }
}

const exportLandingPage = async (id) => {
  try {
    await backendService.exportLandingPage(id)
    toast.add({
      severity: 'success',
      summary: 'Exported',
      detail: 'Landing page exported successfully',
      life: 2000
    })
  } catch (error) {
    console.error('Failed to export:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to export landing page',
      life: 3000
    })
  }
}

const openCloneDialog = (page) => {
  pageToClone.value = page
  cloneName.value = `${page.name} (Copy)`
  cloneSubmitted.value = false
  showCloneDialog.value = true
}

const cloneLandingPage = async () => {
  cloneSubmitted.value = true

  if (!cloneName.value) {
    return
  }

  cloning.value = true
  try {
    const cloned = await backendService.cloneLandingPage(pageToClone.value.id)

    // Update name if different
    if (cloneName.value !== cloned.name) {
      await backendService.updateLandingPage(cloned.id, { name: cloneName.value })
    }

    toast.add({
      severity: 'success',
      summary: 'Cloned',
      detail: 'Landing page cloned successfully',
      life: 3000
    })

    showCloneDialog.value = false
    await fetchLandingPages()
  } catch (error) {
    console.error('Failed to clone:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to clone landing page',
      life: 3000
    })
  } finally {
    cloning.value = false
    cloneSubmitted.value = false
  }
}

const confirmDelete = (page) => {
  pageToDelete.value = page
  showDeleteDialog.value = true
}

const deleteLandingPage = async () => {
  if (!pageToDelete.value) return

  deleting.value = true
  try {
    await backendService.deleteLandingPage(pageToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: 'Landing page deleted successfully',
      life: 3000
    })

    showDeleteDialog.value = false
    pageToDelete.value = null
    await fetchLandingPages()
  } catch (error) {
    console.error('Failed to delete:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete landing page',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

// Import methods
const triggerImportInput = () => {
  importInput.value?.click()
}

const handleImportSelect = async (event) => {
  const file = event.target.files[0]

  if (!file) return

  if (!file.name.endsWith('.html')) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Only HTML files are supported',
      life: 3000
    })
    return
  }

  try {
    const content = await file.text()
    landingPageForm.value.content = content

    // Extract title if present and name is empty
    if (!landingPageForm.value.name) {
      const titleMatch = content.match(/<title>(.*?)<\/title>/i)
      if (titleMatch) {
        landingPageForm.value.name = titleMatch[1]
      } else {
        landingPageForm.value.name = file.name.replace('.html', '')
      }
    }

    toast.add({
      severity: 'success',
      summary: 'Imported',
      detail: `HTML file "${file.name}" loaded successfully`,
      life: 2000
    })
  } catch (error) {
    console.error('Failed to read file:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to read HTML file',
      life: 3000
    })
  } finally {
    // Reset input
    if (importInput.value) {
      importInput.value.value = ''
    }
  }
}

const insertTemplate = () => {
  if (landingPageForm.value.content && landingPageForm.value.content !== DEFAULT_LANDING_PAGE_TEMPLATE) {
    if (!confirm('This will replace your current content. Continue?')) {
      return
    }
  }

  landingPageForm.value.content = DEFAULT_LANDING_PAGE_TEMPLATE
  toast.add({
    severity: 'info',
    summary: 'Template Loaded',
    detail: 'Default template has been inserted',
    life: 2000
  })
}

const resetForm = () => {
  landingPageForm.value = {
    id: null,
    name: '',
    description: '',
    content: ''
  }
  submitted.value = false
}

const onDialogHide = () => {
  resetForm()
  dialogMode.value = 'create'
}

onMounted(() => {
  fetchLandingPages()
})
</script>

<style scoped src="../assets/views/landing-pages.css"></style>
