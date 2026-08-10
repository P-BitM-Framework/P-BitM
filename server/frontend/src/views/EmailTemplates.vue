<template>
  <div class="email-templates-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader title="Email Templates" subtitle="Create and manage campaign email templates">
      <template #actions>
        <Button label="New Template" icon="pi pi-plus" @click="openCreateDialog" />
      </template>
    </PageHeader>

    <!-- Table Card -->
    <Card class="templates-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-title app-section-title">
            <i class="pi pi-envelope"></i>
            Email Templates
            <span class="count-badge">{{ templates.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search templates..."
                class="search-input"
              />
            </IconField>

            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              @click="fetchTemplates"
              :loading="showLoading"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="templates"
          :loading="showLoading"
          :filters="filters"
          :clickableRows="true"
          @row-click="previewTemplate($event.data)"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          class="data-table data-table--interactive"
        >
          <Column field="name" header="Template Name" sortable style="min-width: 250px">
            <template #body="{ data }">
              <div class="template-cell">
                <div class="template-icon">
                  <i class="pi pi-envelope"></i>
                </div>
                <div class="template-details">
                  <strong>{{ data.name }}</strong>
                  <span class="template-subject">{{ data.subject }}</span>
                </div>
              </div>
            </template>
          </Column>

          <Column field="subject" header="Subject Line" sortable></Column>

          <Column field="created_at" header="Created" sortable style="width: 150px">
            <template #body="{ data }">
              <span class="time-ago">
                <i class="pi pi-calendar"></i>
                {{ formatDateLocal(data.created_at) }}
              </span>
            </template>
          </Column>

          <Column header="Actions" style="width: 180px" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-eye"
                  severity="info"
                  text
                  rounded
                  v-tooltip.top="'Preview'"
                  @click.stop="previewTemplate(data)"
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
              <p>No email templates found. Create your first template.</p>
              <Button
                label="Create Template"
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

    <!-- Create/Edit Template Dialog -->
    <Dialog
      v-model:visible="showEditDialog"
      modal
      :header="dialogMode === 'edit' ? 'Edit Email Template' : 'Create Email Template'"
      class="email-template-editor-dialog app-text-editor-dialog"
      content-class="email-template-editor-content"
      :style="{ width: '95vw', maxWidth: '1800px' }"
      :draggable="false"
      @hide="onDialogHide"
    >
      <div class="dialog-layout">
        <!-- Left Sidebar: Settings -->
        <div class="settings-sidebar">
          <!-- Settings Section -->
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-cog"></i>
              Settings
            </h3>

            <div class="field">
              <label for="templateName">Template Name <span class="required">*</span></label>
              <InputText
                id="templateName"
                v-model="templateForm.name"
                placeholder="LinkedIn Phishing Template"
                :invalid="submitted && !templateForm.name"
              />
              <small v-if="submitted && !templateForm.name" class="p-error">Template name is required</small>
            </div>

            <div class="field">
              <label for="description">Description</label>
              <Textarea
                id="description"
                v-model="templateForm.description"
                rows="3"
                placeholder="Brief description..."
              />
            </div>

            <div class="field">
              <label for="subject">Email Subject <span class="required">*</span></label>
              <InputText
                id="subject"
                v-model="templateForm.subject"
                placeholder="Your LinkedIn profile has been viewed"
                :invalid="submitted && !templateForm.subject"
              />
              <small v-if="submitted && !templateForm.subject" class="p-error">Subject is required</small>
            </div>

            <div class="field">
              <label>Content Type</label>
              <SelectButton
                v-model="templateForm.content_type"
                :options="contentTypeOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <Divider />

          <!-- Variables Section -->
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
                v-for="variable in availableVariables"
                :key="variable"
                :value="variable"
                severity="secondary"
                class="variable-tag"
                @click="copyVariable(variable)"
              />
            </div>
          </div>

          <Divider />

          <!-- Attachments Section -->
          <div class="sidebar-section">
            <h3 class="section-heading">
              <i class="pi pi-paperclip"></i>
              Attachments
            </h3>

            <Message severity="info" :closable="false" class="attachment-info-message">
              Use <code v-pre>{{attachment:filename.png}}</code> in HTML
            </Message>

            <FileUpload
              ref="fileUploadRef"
              :multiple="true"
              accept="image/*,application/pdf,.doc,.docx"
              :maxFileSize="5000000"
              @select="onFilesSelect"
              :auto="true"
              :showUploadButton="false"
              :showCancelButton="false"
              class="compact-upload"
            >
              <template #header="{ chooseCallback }">
                <div class="upload-header-compact">
                  <Button
                    label="Select Files"
                    icon="pi pi-plus"
                    @click="chooseCallback()"
                    severity="secondary"
                    outlined
                    size="small"
                    class="w-full"
                  />
                </div>
              </template>

              <template #content="{ files, removeFileCallback }">
                <div v-if="files.length > 0" class="attachments-list-compact">
                  <div
                    v-for="(file, index) in files"
                    :key="file.name + file.size"
                    class="attachment-item-compact"
                  >
                    <div class="attachment-preview-small">
                      <img v-if="file.type.startsWith('image/')" :src="file.objectURL" :alt="file.name" />
                      <i v-else class="pi pi-file"></i>
                    </div>

                    <div class="attachment-info-compact">
                      <span class="file-name-compact" :title="file.name">{{ file.name }}</span>
                      <span class="file-size-compact">{{ formatFileSize(file.size) }}</span>
                    </div>

                    <div class="attachment-actions-compact">
                      <Button
                        icon="pi pi-code"
                        severity="secondary"
                        text
                        size="small"
                        v-tooltip.top="'Copy tag'"
                        @click="copyAttachmentTag(file.name)"
                      />
                      <Button
                        icon="pi pi-times"
                        severity="danger"
                        text
                        size="small"
                        @click="removeFileCallback(index)"
                      />
                    </div>
                  </div>
                </div>
              </template>

              <template #empty>
                <div class="empty-upload-compact" @click="$refs.fileUploadRef?.choose()">
                  <i class="pi pi-cloud-upload"></i>
                  <p>Click to select files</p>
                </div>
              </template>
            </FileUpload>
          </div>

          <Divider />

          <!-- Tips Section -->
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
                <span>Inline CSS for better rendering</span>
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
          <!-- HTML Content -->
          <div v-if="templateForm.content_type === 'html'">
            <CodeCard
              v-model="templateForm.html_content"
              title="Email HTML Content"
              icon="pi pi-envelope"
              language="html"
              :required="true"
              :error="submitted && !templateForm.html_content ? 'HTML content is required' : ''"
            />
          </div>

          <!-- Text Content -->
          <div v-else class="text-editor-container">
            <div class="text-editor-header">
              <div class="header-left">
                <i class="pi pi-align-left"></i>
                <span>Plain Text Content</span>
                <Badge v-if="!templateForm.text_content" value="Required" severity="danger" />
              </div>
              <div class="header-right">
                <span class="stat-item">
                  <i class="pi pi-list"></i>
                  {{ textLineCount }} lines
                </span>
                <Button
                  icon="pi pi-copy"
                  severity="secondary"
                  text
                  rounded
                  size="small"
                  @click="copyTextContent"
                  v-tooltip.top="'Copy to clipboard'"
                />
              </div>
            </div>
            <Textarea
              v-model="templateForm.text_content"
              rows="20"
              placeholder="Hello {{first_name}},&#10;&#10;This is a plain text email..."
              :invalid="submitted && !templateForm.text_content"
              class="text-content-area"
            />
            <small v-if="submitted && !templateForm.text_content" class="p-error">Text content is required</small>
          </div>
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
            @click="previewCurrentTemplate"
          />
          <Button
            :label="dialogMode === 'edit' ? 'Update' : 'Create'"
            icon="pi pi-check"
            :loading="saving"
            @click="saveTemplate"
          />
        </div>
      </template>
    </Dialog>

    <!-- Preview Dialog -->
    <Dialog
      v-model:visible="showPreviewDialog"
      modal
      header="Email Preview"
      :style="{ width: '900px' }"
      :draggable="false"
    >
      <div class="preview-container">
        <div class="email-header-info">
          <div class="info-row">
            <strong>Template:</strong>
            <span>{{ selectedTemplate?.name }}</span>
          </div>
          <div class="info-row">
            <strong>Subject:</strong>
            <span>{{ selectedTemplate?.subject }}</span>
          </div>
        </div>

        <div class="email-preview-frame">
          <iframe
            :srcdoc="selectedTemplate?.html_content || selectedTemplate?.text_content"
            sandbox=""
            frameborder="0"
            class="preview-iframe"
          ></iframe>
        </div>
      </div>

      <template #footer>
        <Button label="Close" severity="secondary" text @click="showPreviewDialog = false" />
        <Button
          label="Edit Template"
          icon="pi pi-pencil"
          @click="editFromPreview"
        />
      </template>
    </Dialog>

    <!-- Clone Dialog -->
    <Dialog
      v-model:visible="showCloneDialog"
      modal
      header="Clone Email Template"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="field">
        <label for="cloneName">New Template Name <span class="required">*</span></label>
        <InputText
          id="cloneName"
          v-model="cloneName"
          :placeholder="`${templateToClone?.name} (Copy)`"
          :invalid="cloneSubmitted && !cloneName"
          autofocus
        />
        <small v-if="cloneSubmitted && !cloneName" class="p-error">Name is required</small>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showCloneDialog = false" />
        <Button
          label="Clone Template"
          icon="pi pi-copy"
          :loading="cloning"
          @click="cloneTemplate"
        />
      </template>
    </Dialog>

    <DeleteResourceDialog
      v-model:visible="showDeleteDialog"
      header="Delete Email Template"
      :subject="templateToDelete?.name"
      confirm-label="Delete Template"
      :loading="deleting"
      @confirm="deleteTemplate"
    >
      <p>This action cannot be undone</p>
      <Message severity="warn" :closable="false" class="mt-3">
        All campaigns using this template will continue to work with their saved version.
      </Message>
    </DeleteResourceDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import { backendService } from '@/services/backend'
import CodeCard from '@/components/default/CodeCard.vue'
import { formatDateLocal } from '@/utils/utils'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import FileUpload from 'primevue/fileupload'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DeleteResourceDialog from '@/components/default/DeleteResourceDialog.vue'

const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const deleting = ref(false)
const cloning = ref(false)
const submitted = ref(false)
const cloneSubmitted = ref(false)

const templates = ref([])
const showEditDialog = ref(false)
const showPreviewDialog = ref(false)
const showCloneDialog = ref(false)
const showDeleteDialog = ref(false)
const dialogMode = ref('create')

const selectedTemplate = ref(null)
const templateToDelete = ref(null)
const templateToClone = ref(null)
const cloneName = ref('')

const templateForm = ref({
  id: null,
  name: '',
  description: '',
  subject: '',
  content_type: 'html',
  html_content: '',
  text_content: '',
  attachments: []
})

const contentTypeOptions = [
  { label: 'HTML', value: 'html' },
  { label: 'Plain Text', value: 'text' }
]

const availableVariables = [
  '{{phishing_url}}',
  '{{first_name}}',
  '{{last_name}}',
  '{{email}}',
  '{{company}}',
  '{{position}}'
]

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Computed
const textLineCount = computed(() => {
  return (templateForm.value.text_content || '').split('\n').length
})

// Methods
const fetchTemplates = async () => {
  loading.value = true
  try {
    const data = await backendService.getEmailTemplates()
    templates.value = data.templates || []
  } catch (error) {
    console.error('Failed to fetch email templates:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load email templates',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  resetTemplateForm()
  showEditDialog.value = true
}

const openEditDialog = (template) => {
  dialogMode.value = 'edit'
  templateForm.value = {
    ...template,
    content_type: template.html_content ? 'html' : 'text',
    attachments: template.attachments || []
  }
  showEditDialog.value = true
}

const saveTemplate = async () => {
  submitted.value = true

  const isHtml = templateForm.value.content_type === 'html'
  const hasContent = isHtml ? templateForm.value.html_content : templateForm.value.text_content

  if (!templateForm.value.name || !templateForm.value.subject || !hasContent) {
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
      await backendService.updateEmailTemplate(templateForm.value.id, templateForm.value)
      toast.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Email template updated successfully',
        life: 3000
      })
    } else {
      await backendService.createEmailTemplate(templateForm.value)
      toast.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Email template created successfully',
        life: 3000
      })
    }

    showEditDialog.value = false
    await fetchTemplates()
  } catch (error) {
    console.error('Failed to save template:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to save template',
      life: 3000
    })
  } finally {
    saving.value = false
    submitted.value = false
  }
}

const copyAttachmentTag = (filename) => {
  const tag = `{{attachment:${filename}}}`
  navigator.clipboard.writeText(tag)
  toast.add({
    severity: 'success',
    summary: 'Copied',
    detail: `Tag copied: ${tag}`,
    life: 2000
  })
}

const copyTextContent = async () => {
  try {
    await navigator.clipboard.writeText(templateForm.value.text_content || '')
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: 'Text content copied to clipboard',
      life: 2000
    })
  } catch (_error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy to clipboard',
      life: 3000
    })
  }
}

const previewTemplate = (template) => {
  selectedTemplate.value = template
  showPreviewDialog.value = true
}

const previewCurrentTemplate = () => {
  selectedTemplate.value = { ...templateForm.value }
  showPreviewDialog.value = true
}

const editFromPreview = () => {
  showPreviewDialog.value = false
  if (selectedTemplate.value.id) {
    openEditDialog(selectedTemplate.value)
  }
}

const openCloneDialog = (template) => {
  templateToClone.value = template
  cloneName.value = `${template.name} (Copy)`
  cloneSubmitted.value = false
  showCloneDialog.value = true
}

const cloneTemplate = async () => {
  cloneSubmitted.value = true

  if (!cloneName.value) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Please enter a name for the cloned template',
      life: 3000
    })
    return
  }

  cloning.value = true
  try {
    await backendService.cloneEmailTemplate(templateToClone.value.id, { name: cloneName.value })
    toast.add({
      severity: 'success',
      summary: 'Cloned',
      detail: `Template "${templateToClone.value.name}" cloned successfully`,
      life: 3000
    })
    showCloneDialog.value = false
    cloneName.value = ''
    await fetchTemplates()
  } catch (error) {
    console.error('Failed to clone template:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to clone template',
      life: 3000
    })
  } finally {
    cloning.value = false
    cloneSubmitted.value = false
  }
}

const confirmDelete = (template) => {
  templateToDelete.value = template
  showDeleteDialog.value = true
}

const deleteTemplate = async () => {
  if (!templateToDelete.value) return

  deleting.value = true
  try {
    await backendService.deleteEmailTemplate(templateToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: `Template "${templateToDelete.value.name}" deleted successfully`,
      life: 3000
    })
    showDeleteDialog.value = false
    templateToDelete.value = null
    await fetchTemplates()
  } catch (error) {
    console.error('Failed to delete template:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete template',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

const onFilesSelect = (event) => {
  const files = event.files
  for (const file of files) {
    const reader = new FileReader()
    reader.onload = (e) => {
      templateForm.value.attachments.push({
        name: file.name,
        size: file.size,
        type: file.type,
        data: e.target.result
      })
    }
    reader.readAsDataURL(file)
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
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
  }
}

const resetTemplateForm = () => {
  templateForm.value = {
    id: null,
    name: '',
    description: '',
    subject: '',
    content_type: 'html',
    html_content: '',
    text_content: '',
    attachments: []
  }
  submitted.value = false
}

const onDialogHide = () => {
  resetTemplateForm()
  dialogMode.value = 'create'
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped src="../assets/views/email-templates.css"></style>
