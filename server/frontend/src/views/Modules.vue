<template>
  <div class="modules-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader title="Modules" subtitle="Create parameterized JavaScript modules">
      <template #actions>
        <Button label="New Module" icon="pi pi-plus" @click="openCreateDialog" />
      </template>
    </PageHeader>

    <!-- Table Card -->
    <Card class="modules-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-name app-section-title">
            <i class="pi pi-bolt"></i>
            Modules
            <span class="count-badge">{{ modules.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search modules..."
                class="search-input"
              />
            </IconField>

            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              @click="fetchModules"
              :loading="showLoading"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="modules"
          :loading="showLoading"
          :filters="filters"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          @row-click="openEditDialog($event.data)"
          class="data-table data-table--interactive"
        >
          <Column field="name" header="Module" sortable style="min-width: 250px">
            <template #body="{ data }">
              <div class="module-cell">
                <div class="module-details">
                  <strong>{{ data.name }}</strong>
                  <span class="module-description">{{ data.description || 'No description' }}</span>
                </div>
              </div>
            </template>
          </Column>

          <Column field="category" header="Category" sortable style="width: 180px">
            <template #body="{ data }">
              <Tag
                v-if="data.category"
                :value="data.category"
                :severity="getCategorySeverity(data.category)"
              />
              <span v-else class="text-muted">-</span>
            </template>
          </Column>

          <Column field="inputs" header="Parameters" style="width: 120px">
            <template #body="{ data }">
              <Tag
                v-if="data.inputs && data.inputs.length > 0"
                :value="`${data.inputs.length} param${data.inputs.length > 1 ? 's' : ''}`"
                severity="info"
              />
              <span v-else class="text-muted">-</span>
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

          <Column header="Actions" style="width: 180px" headerClass="sticky-actions" bodyClass="sticky-actions">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  @click.stop="openEditDialog(data)"
                  v-tooltip.bottom="'Edit'"
                />
                <Button
                  icon="pi pi-copy"
                  severity="secondary"
                  text
                  rounded
                  @click.stop="openCloneDialog(data)"
                  v-tooltip.bottom="'Clone'"
                />
                <Button
                  icon="pi pi-download"
                  severity="secondary"
                  text
                  rounded
                  @click.stop="exportModule(data.id)"
                  v-tooltip.bottom="'Export'"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  @click.stop="openDeleteDialog(data)"
                  v-tooltip.bottom="'Delete'"
                />
              </div>
            </template>
          </Column>

          <template #empty>
            <div class="empty-table">
              <i class="pi pi-inbox"></i>
              <p>No modules found. Create your first module.</p>
            </div>
          </template>
        </DataTable>
      </template>
    </Card>
    </DelayedContent>

    <!-- Module Dialog -->
    <ModuleDialog
      v-model="showEditDialog"
      :mode="dialogMode"
      :module="selectedModule"
      @save="handleModuleSave"
    />

    <!-- Clone Dialog -->
    <Dialog
      v-model:visible="showCloneDialog"
      header="Clone Module"
      :style="{ width: '500px' }"
      modal
      :draggable="false"
    >
      <p class="mb-3">Clone <strong>{{ moduleToClone?.name }}</strong></p>
      <div class="field">
        <label for="cloneName">New Module Name <span class="required">*</span></label>
        <InputText
          id="cloneName"
          v-model="cloneName"
          placeholder="Enter module name"
          :invalid="cloneSubmitted && !cloneName"
        />
        <small v-if="cloneSubmitted && !cloneName" class="p-error">Name is required</small>
      </div>

      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          @click="showCloneDialog = false"
        />
        <Button
          label="Clone"
          icon="pi pi-copy"
          @click="cloneModule"
          :loading="cloning"
          :disabled="!cloneName"
        />
      </template>
    </Dialog>

    <!-- Delete Dialog -->
    <Dialog
      v-model:visible="showDeleteDialog"
      header="Delete Module"
      :style="{ width: '450px' }"
      modal
      :draggable="false"
    >
      <div class="dialog-content">
        <div class="dialog-icon">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <h3>Are you sure?</h3>
        <p>
          Do you really want to delete <strong>{{ moduleToDelete?.name }}</strong>?
          This action cannot be undone
        </p>
      </div>

      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          @click="showDeleteDialog = false"
        />
        <Button
          label="Delete"
          severity="danger"
          icon="pi pi-trash"
          @click="deleteModule"
          :loading="deleting"
        />
      </template>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { FilterMatchMode } from '@primevue/core/api'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import ModuleDialog from '@/components/dashboard/ModuleDialog.vue'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const toast = useToast()

// State
const modules = ref([])
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const deleting = ref(false)
const cloning = ref(false)

const showEditDialog = ref(false)
const showCloneDialog = ref(false)
const showDeleteDialog = ref(false)

const dialogMode = ref('create')
const cloneSubmitted = ref(false)

const selectedModule = ref(null)
const moduleToDelete = ref(null)
const moduleToClone = ref(null)
const cloneName = ref('')

// Filters
const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Methods
onMounted(() => {
  fetchModules()
})

const formatDateLocal = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

async function fetchModules() {
  loading.value = true
  try {
    const data = await backendService.getModules()
    modules.value = data.modules || []
  } catch (error) {
    console.error('Failed to fetch modules:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load modules',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  selectedModule.value = null
  showEditDialog.value = true
}

function openEditDialog(data) {
  dialogMode.value = 'edit'
  selectedModule.value = data
  showEditDialog.value = true
}

async function handleModuleSave(moduleData) {
  saving.value = true
  try {
    const { id, ...payload } = moduleData
    if (dialogMode.value === 'edit') {
      await backendService.updateModule(id, payload)
      toast.add({
        severity: 'success',
        summary: 'Module Updated',
        detail: `${moduleData.name} updated successfully`,
        life: 3000
      })
    } else {
      await backendService.createModule(payload)
      toast.add({
        severity: 'success',
        summary: 'Module Created',
        detail: `${moduleData.name} created successfully`,
        life: 3000
      })
    }

    showEditDialog.value = false
    await fetchModules()
  } catch (error) {
    console.error('Failed to save module:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save module: ' + error.message,
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

function openCloneDialog(data) {
  moduleToClone.value = data
  cloneName.value = data.name + ' (Copy)'
  cloneSubmitted.value = false
  showCloneDialog.value = true
}

async function cloneModule() {
  if (!cloneName.value || !moduleToClone.value) {
    cloneSubmitted.value = true
    return
  }

  cloning.value = true
  try {
    const cloned = await backendService.cloneModule(moduleToClone.value.id)

    if (cloneName.value !== cloned.name) {
      await backendService.updateModule(cloned.id, { ...cloned, name: cloneName.value })
    }

    toast.add({
      severity: 'success',
      summary: 'Module Cloned',
      detail: `${cloneName.value} created successfully`,
      life: 3000
    })

    showCloneDialog.value = false
    await fetchModules()
  } catch (error) {
    console.error('Failed to clone module:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to clone module: ' + error.message,
      life: 3000
    })
  } finally {
    cloning.value = false
  }
}

function openDeleteDialog(data) {
  moduleToDelete.value = data
  showDeleteDialog.value = true
}

async function deleteModule() {
  if (!moduleToDelete.value) return

  deleting.value = true
  try {
    await backendService.deleteModule(moduleToDelete.value.id)

    toast.add({
      severity: 'success',
      summary: 'Module Deleted',
      detail: `${moduleToDelete.value.name} deleted successfully`,
      life: 3000
    })

    showDeleteDialog.value = false
    await fetchModules()
  } catch (error) {
    console.error('Failed to delete module:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete module: ' + error.message,
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

async function exportModule(id) {
  try {
    await backendService.exportModule(id)
    toast.add({
      severity: 'success',
      summary: 'Module Exported',
      detail: 'Module exported successfully',
      life: 3000
    })
  } catch (error) {
    console.error('Failed to export module:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to export module: ' + error.message,
      life: 3000
    })
  }
}

function getCategorySeverity(category) {
  const severityMap = {
    'Initial Access': 'info',
    'Execution': 'warn',
    'Persistence': 'warn',
    'Privilege Escalation': 'danger',
    'Credential Access': 'danger',
    'Discovery': 'info',
    'Lateral Movement': 'warn',
    'Collection': 'info',
    'Exfiltration': 'danger',
    'Command & Control': 'danger',
    'Post Exploitation': 'danger',
    'Social Engineering': 'warn',
    'Browser Exploitation': 'danger',
    'Cross-Site Scripting': 'danger',
    'Clickjacking': 'warn',
    'Custom': 'secondary'
  }
  return severityMap[category] || 'secondary'
}

</script>

<style scoped>
/* Base Layout */
.modules-view {
  padding: var(--page-padding);
  max-width: var(--content-max-width);
  margin: 0 auto;
  min-height: 100vh;
}

/* Table Card */
.modules-table-card :deep(.p-card-body) {
  padding: 0;
}

.modules-table-card :deep(.p-card-content) {
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

.section-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.section-name i {
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

/* Module Cell */
.module-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.module-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.module-details strong {
  font-weight: 600;
  color: var(--color-heading);
}

.module-description {
  font-size: 0.813rem;
  color: var(--color-text-mute);
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
.empty-table {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 2rem;
  color: var(--color-text-mute);
}

.empty-table i {
  font-size: 3rem;
  opacity: 0.5;
}

/* Dialog Content */
.dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 1rem;
}

.dialog-icon {
  font-size: 3rem;
  color: var(--orange-500);
  margin-bottom: 1rem;
}

.dialog-content h3 {
  margin: 0 0 1rem 0;
  color: var(--color-heading);
}

.dialog-content p {
  color: var(--color-text-mute);
  margin: 0;
}

/* Form Field */
.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-heading);
}

.required {
  color: var(--red-500);
}

.p-error {
  color: var(--red-500);
  font-size: 0.813rem;
}

.text-muted {
  color: var(--color-text-mute);
}

.mb-3 {
  margin-bottom: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .modules-view {
    padding: 1rem;
  }

  .search-input {
    width: 100%;
  }

  .header-content h1 {
    font-size: 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
