<template>
  <DelayedContent :loading="loading" :show-indicator="showLoading">
  <div class="target-list-detail app-page" v-if="targetList">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          @click="$router.push({ name: 'target-lists' })"
        />
        <div class="header-content">
          <h1>{{ targetList?.name || 'Loading...' }}</h1>
          <p v-if="targetList?.description" class="subtitle">
            {{ targetList.description }}
          </p>
          <p v-if="targetList?.company" class="subtitle">
            <i class="pi pi-building"></i> {{ targetList.company }}
          </p>
        </div>
      </div>

      <div class="header-actions">
        <Button
          icon="pi pi-pencil"
          v-tooltip.bottom="'Edit List'"
          severity="secondary"
          outlined
          @click="showEditListDialog = true"
        />
        <Button
          icon="pi pi-trash"
          v-tooltip.bottom="'Delete List'"
          severity="danger"
          outlined
          @click="confirmDeleteList"
        />
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row metrics-grid">
      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-users"></i>
            <div class="stat-text">
              <div class="stat-value">{{ targets.length }}</div>
              <div class="stat-label">Total Targets</div>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-check-circle"></i>
            <div class="stat-text">
              <div class="stat-value">{{ validTargets }}</div>
              <div class="stat-label">Valid Emails</div>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-calendar"></i>
            <div class="stat-text">
              <div class="stat-value">{{ formatDateLocal(targetList?.created_at) }}</div>
              <div class="stat-label">Created</div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Table Card -->
    <Card class="target-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-title app-section-title">
            <i class="pi pi-users"></i>
            Targets
            <span class="count-badge">{{ targets.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search targets..."
                class="search-input"
              />
            </IconField>

            <Button
              label="Add Target"
              icon="pi pi-plus"
              @click="openAddDialog()"
            />
            <button
              id="target-import-menu-button"
              type="button"
              class="import-menu-trigger"
              aria-haspopup="menu"
              aria-controls="target-import-menu"
              @click="toggleImportMenu"
            >
              <i class="pi pi-download" aria-hidden="true"></i>
              <span>Import</span>
              <i class="pi pi-angle-down import-menu-chevron" aria-hidden="true"></i>
            </button>
            <Menu
              ref="importMenu"
              id="target-import-menu"
              :model="importActions"
              popup
            />
            <Button
              icon="pi pi-file-export"
              label="Export"
              severity="secondary"
              outlined
              :loading="exporting"
              @click="exportTargets"
            />
            <Button
              v-if="selectedTargets.length > 0"
              :label="`Delete (${selectedTargets.length})`"
              icon="pi pi-trash"
              severity="danger"
              @click="confirmBulkDelete"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="targets"
          :loading="loading"
          :filters="filters"
          paginator
          :rows="25"
          :rowsPerPageOptions="[25, 50, 100]"
          selectionMode="multiple"
          v-model:selection="selectedTargets"
          dataKey="id"
          class="data-table data-table--interactive"
        >
          <Column selectionMode="multiple" style="width: 3rem" exportable="false"></Column>
          <Column field="email" header="Email" sortable style="min-width: 250px">
            <template #body="{ data }">
              <strong>{{ data.email }}</strong>
            </template>
          </Column>
          <Column field="first_name" header="First Name" sortable></Column>
          <Column field="last_name" header="Last Name" sortable></Column>
          <Column field="position" header="Position" sortable></Column>

          <Column header="Actions" style="width: 8rem" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <Button
                icon="pi pi-pencil"
                text
                rounded
                severity="secondary"
                v-tooltip.top="'Edit'"
                @click="editTarget(data)"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                v-tooltip.top="'Delete'"
                @click="confirmDeleteTarget(data)"
              />
            </template>
          </Column>

          <template #empty>
            <div class="empty-state">
              <i class="pi pi-inbox"></i>
              <p>No targets found. Add your first target.</p>
              <Button
                label="Add Target"
                icon="pi pi-plus"
                @click="openAddDialog()"
                size="small"
                class="mt-2"
              />
            </div>
          </template>
        </DataTable>
      </template>
    </Card>

    <!-- ==================== DIALOGS ==================== -->

    <!-- Edit List Dialog -->
    <Dialog
      v-model:visible="showEditListDialog"
      modal
      header="Edit Target List"
      :style="{ width: '600px' }"
      :draggable="false"
      @hide="resetEditListForm"
    >
      <div class="form-grid">
        <div class="field">
          <label for="name">Name <span class="required">*</span></label>
          <InputText
            id="name"
            v-model="editList.name"
            class="w-full"
            placeholder="Target List Name"
            :invalid="submitted && !editList.name"
          />
          <small v-if="submitted && !editList.name" class="p-error">Name is required</small>
        </div>

        <div class="field">
          <label for="description">Description</label>
          <InputText
            id="description"
            v-model="editList.description"
            class="w-full"
            placeholder="Description"
          />
        </div>

        <div class="field">
          <label for="company">Company</label>
          <InputText
            id="company"
            v-model="editList.company"
            class="w-full"
            placeholder="Acme Corp"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showEditListDialog = false" />
        <Button
          label="Save List"
          :loading="saving"
          @click="updateList"
        />
      </template>
    </Dialog>

    <!-- Add/Edit Single Target Dialog -->
    <Dialog
      v-model:visible="showAddDialog"
      modal
      :header="dialogMethod + ' Target'"
      :style="{ width: '600px' }"
      :draggable="false"
      @hide="resetTargetForm"
    >
      <div class="form-grid">
        <div class="field">
          <label for="email">Email <span class="required">*</span></label>
          <InputText
            id="email"
            v-model="newTarget.email"
            class="w-full"
            placeholder="john@example.com"
            :invalid="submitted && !newTarget.email"
          />
          <small v-if="submitted && !newTarget.email" class="p-error">Email is required</small>
        </div>

        <div class="dialog-row">
          <div class="field">
            <label for="firstName">First Name</label>
            <InputText
              id="firstName"
              v-model="newTarget.first_name"
              class="w-full"
              placeholder="John"
            />
          </div>

          <div class="field">
            <label for="lastName">Last Name</label>
            <InputText
              id="lastName"
              v-model="newTarget.last_name"
              class="w-full"
              placeholder="Doe"
            />
          </div>
        </div>

        <div class="dialog-row">
          <div class="field">
            <label for="position">Position</label>
            <InputText
              id="position"
              v-model="newTarget.position"
              class="w-full"
              placeholder="Manager"
            />
          </div>

          <div class="field">
            <label for="department">Department</label>
            <InputText
              id="department"
              v-model="newTarget.department"
              class="w-full"
              placeholder="Sales"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showAddDialog = false" />
        <Button
          :label="dialogMethod + ' Target'"
          :loading="saving"
          @click="saveTarget"
        />
      </template>
    </Dialog>

    <!-- Import CSV Dialog -->
    <Dialog
      v-model:visible="showImportDialog"
      modal
      header="Import Targets from CSV"
      :style="{ width: '700px' }"
      :draggable="false"
      @hide="resetImportForm"
    >
      <div class="import-container">
        <FileUpload
          ref="fileUploader"
          mode="basic"
          name="csv"
          accept=".csv"
          :maxFileSize="5000000"
          chooseLabel="Choose CSV File"
          @select="onFileSelect"
          :auto="false"
          class="w-full"
        />

        <Message severity="info" :closable="false" class="mt-3">
          <div>
            <strong>CSV format:</strong>
            <p class="mb-2 mt-2">Required: <code>email</code></p>
            <p class="mb-2">Optional: <code>first_name, last_name, position, department</code></p>
            <p class="mb-0 mt-3"><strong>Example:</strong></p>
            <code class="block mt-1">email,first_name,last_name,position</code>
            <code class="block">john@example.com,John,Doe,Manager</code>
            <code class="block">jane@example.com,Jane,Smith,Developer</code>
          </div>
        </Message>

        <div v-if="csvPreview.length" class="csv-preview mt-4">
          <div class="preview-header">
            <h4>Preview (first 5 rows)</h4>
            <Tag :value="`${csvData.length} total`" severity="info" />
          </div>
          <DataTable :value="csvPreview" size="small" class="data-table mt-2">
            <Column field="email" header="Email"></Column>
            <Column field="first_name" header="First Name"></Column>
            <Column field="last_name" header="Last Name"></Column>
            <Column field="position" header="Position"></Column>
          </DataTable>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showImportDialog = false" />
        <Button
          label="Import"
          icon="pi pi-upload"
          :disabled="!csvData.length"
          :loading="importing"
          @click="importCSV"
        />
      </template>
    </Dialog>

    <!-- Bulk Add Dialog -->
    <Dialog
      v-model:visible="showBulkDialog"
      modal
      header="Bulk Add Targets"
      :style="{ width: '700px' }"
      :draggable="false"
      @hide="resetBulkForm"
    >
      <div class="bulk-container">
        <p class="mb-3">Enter one email per line. Optionally include name and position separated by commas.</p>

        <Textarea
          v-model="bulkText"
          rows="12"
          class="w-full"
          placeholder="john@example.com&#10;jane@example.com, Jane Smith, Developer&#10;bob@example.com, Bob Johnson, Manager, Sales"
        />

        <Message severity="info" :closable="false" class="mt-3">
          <div>
            <p class="mb-2"><strong>Supported formats:</strong></p>
            <code class="block">email</code>
            <code class="block">email, first_name last_name</code>
            <code class="block">email, first_name last_name, position</code>
            <code class="block">email, first_name last_name, position, department</code>
          </div>
        </Message>

        <div v-if="bulkPreview.length" class="bulk-preview mt-4">
          <div class="preview-header">
            <h4>Preview</h4>
            <Tag :value="`${bulkPreview.length} targets`" severity="info" />
          </div>
          <DataTable :value="bulkPreview" size="small" class="data-table mt-2" :rows="5" paginator>
            <Column field="email" header="Email"></Column>
            <Column field="first_name" header="First Name"></Column>
            <Column field="last_name" header="Last Name"></Column>
            <Column field="position" header="Position"></Column>
          </DataTable>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showBulkDialog = false" />
        <Button
          label="Add Targets"
          icon="pi pi-check"
          :disabled="!bulkText.trim()"
          :loading="saving"
          @click="bulkAddTargets"
        />
      </template>
    </Dialog>

    <DeleteResourceDialog
      v-model:visible="showDeleteTargetDialog"
      header="Delete Target"
      :subject="targetToDelete?.email"
      :loading="deleting"
      @confirm="deleteTarget"
    >
      <p>This action cannot be undone</p>
    </DeleteResourceDialog>

    <DeleteResourceDialog
      v-model:visible="showBulkDeleteDialog"
      header="Delete Multiple Targets"
      :subject="`${selectedTargets.length} targets`"
      :confirm-label="`Delete ${selectedTargets.length} Targets`"
      :loading="deleting"
      width="500px"
      @confirm="deleteBulkTargets"
    >
      <template #title>Delete {{ selectedTargets.length }} targets?</template>
      <p>This will permanently delete all selected targets. This action cannot be undone</p>

      <div v-if="selectedTargets.length <= 5" class="target-list-preview mt-3">
        <p><strong>Targets to delete:</strong></p>
        <ul>
          <li v-for="target in selectedTargets" :key="target.id">{{ target.email }}</li>
        </ul>
      </div>

      <Message severity="warn" :closable="false">
        This action cannot be undone
      </Message>
    </DeleteResourceDialog>

    <DeleteResourceDialog
      v-model:visible="showDeleteListDialog"
      header="Delete Target List"
      :subject="targetList?.name"
      confirm-label="Delete List"
      :loading="deleting"
      width="500px"
      @confirm="deleteList"
    >
      <p>
        This will permanently delete this list and all
        <strong>{{ targets.length }} targets</strong> in it.
      </p>

      <Message severity="warn" :closable="false">
        <span>
          <strong>Warning:</strong>
          This list has been used {{ targetList?.usage_count || 0 }} times in campaigns.
        </span>
      </Message>
    </DeleteResourceDialog>

  </div>

  <!-- List Not Found -->
  <div v-else class="list-not-found">
    <div class="empty-state">
      <i class="pi pi-exclamation-circle"></i>
      <h2>Target List Not Found</h2>
      <p>The target list you're looking for doesn't exist or has been deleted.</p>
      <Button
        label="Back to Lists"
        icon="pi pi-arrow-left"
        @click="$router.push({ name: 'target-lists' })"
        class="mt-3"
      />
    </div>
  </div>
  </DelayedContent>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import FileUpload from 'primevue/fileupload'
import Menu from 'primevue/menu'
import { backendService } from '@/services/backend'
import { formatDateLocal } from '@/utils/utils'
import DeleteResourceDialog from '@/components/default/DeleteResourceDialog.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import { useTargetImport } from '@/composables/useTargetImport'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const route = useRoute()
const router = useRouter()
const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const deleting = ref(false)
const exporting = ref(false)
const submitted = ref(false)

const targetList = ref(null)
const targets = ref([])
const selectedTargets = ref([])

const showEditListDialog = ref(false)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const showBulkDialog = ref(false)
const showDeleteTargetDialog = ref(false)
const showBulkDeleteDialog = ref(false)
const showDeleteListDialog = ref(false)
const importMenu = ref(null)

const targetToDelete = ref(null)

const editList = ref({
  name: '',
  description: '',
  company: ''
})

const newTarget = ref({
  email: '',
  first_name: '',
  last_name: '',
  position: '',
  department: ''
})

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Import Actions Menu
const importActions = ref([
  {
    label: 'Import CSV',
    icon: 'pi pi-file',
    command: () => { showImportDialog.value = true }
  },
  {
    label: 'Bulk Add',
    icon: 'pi pi-list',
    command: () => { showBulkDialog.value = true }
  }
])

const toggleImportMenu = (event) => {
  importMenu.value?.toggle(event)
}

// Computed
const validTargets = computed(() => {
  return targets.value.filter(t => t.email && t.email.includes('@')).length
})

const dialogMethod = computed(() => newTarget.value.id ? 'Edit' : 'Add')

// Methods
const fetchList = async () => {
  loading.value = true
  try {
    const data = await backendService.getTargetList(route.params.listId)
    targetList.value = data
    editList.value = { name: data.name, description: data.description, company: data.company }

    if (data.targets) {
      targets.value = Array.isArray(data.targets) ? data.targets : []
    } else {
      const targetsData = await backendService.getTargets(route.params.listId)
      targets.value = targetsData.targets || []
    }
  } catch (error) {
    console.error('Failed to fetch target list:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load target list',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const {
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
} = useTargetImport({
  getListId: () => route.params.listId,
  refresh: fetchList,
  saving,
  toast,
  showImportDialog,
  showBulkDialog
})

const openAddDialog = () => {
  resetTargetForm()
  showAddDialog.value = true
}

const updateList = async () => {
  submitted.value = true

  if (!editList.value.name) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'List name is required',
      life: 3000
    })
    return
  }

  saving.value = true
  try {
    await backendService.updateTargetList(route.params.listId, editList.value)
    toast.add({
      severity: 'success',
      summary: 'Updated',
      detail: 'Target list updated successfully',
      life: 3000
    })
    showEditListDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('Failed to update target list:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to update target list',
      life: 3000
    })
  } finally {
    saving.value = false
    submitted.value = false
  }
}

const saveTarget = async () => {
  submitted.value = true

  if (!newTarget.value.email || !newTarget.value.email.includes('@')) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Please enter a valid email address',
      life: 3000
    })
    return
  }

  saving.value = true
  try {
    if (newTarget.value.id) {
      await backendService.updateTarget(route.params.listId, newTarget.value.id, newTarget.value)
      toast.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Target updated successfully',
        life: 3000
      })
    } else {
      await backendService.addTarget(route.params.listId, newTarget.value)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Target added successfully',
        life: 3000
      })
    }

    showAddDialog.value = false
    await fetchList()
  } catch (error) {
    console.error('Failed to save target:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to save target',
      life: 3000
    })
  } finally {
    saving.value = false
    submitted.value = false
  }
}

const resetEditListForm = () => {
  if (targetList.value) {
    editList.value = {
      name: targetList.value.name,
      description: targetList.value.description,
      company: targetList.value.company
    }
  }
  submitted.value = false
}

const resetTargetForm = () => {
  newTarget.value = {
    email: '',
    first_name: '',
    last_name: '',
    position: '',
    department: ''
  }
  submitted.value = false
}

const editTarget = (target) => {
  newTarget.value = { ...target }
  showAddDialog.value = true
}

const confirmDeleteTarget = (target) => {
  targetToDelete.value = target
  showDeleteTargetDialog.value = true
}

const deleteTarget = async () => {
  if (!targetToDelete.value) return

  deleting.value = true
  try {
    await backendService.deleteTarget(route.params.listId, targetToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: 'Target deleted successfully',
      life: 3000
    })
    showDeleteTargetDialog.value = false
    targetToDelete.value = null
    await fetchList()
  } catch (error) {
    console.error('Failed to delete target:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete target',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

const confirmBulkDelete = () => {
  if (!selectedTargets.value.length) return
  showBulkDeleteDialog.value = true
}

const deleteBulkTargets = async () => {
  if (!selectedTargets.value.length) return

  deleting.value = true
  try {
    const targetIds = selectedTargets.value.map(t => t.id)
    await backendService.bulkDeleteTargets(route.params.listId, targetIds)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: `${selectedTargets.value.length} targets deleted successfully`,
      life: 3000
    })
    showBulkDeleteDialog.value = false
    selectedTargets.value = []
    await fetchList()
  } catch (error) {
    console.error('Failed to delete targets:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete targets',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

const confirmDeleteList = () => {
  showDeleteListDialog.value = true
}

const deleteList = async () => {
  deleting.value = true
  try {
    await backendService.deleteTargetList(route.params.listId)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: 'Target list deleted successfully',
      life: 3000
    })
    router.push({ name: 'target-lists' })
  } catch (error) {
    console.error('Failed to delete list:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete target list',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

const exportTargets = async () => {
  if (!targets.value.length) {
    toast.add({
      severity: 'warn',
      summary: 'No Data',
      detail: 'No targets to export',
      life: 3000
    })
    return
  }

  exporting.value = true
  try {
    const response = await backendService.exportTargetsCsv(route.params.listId)

    const blob = new Blob([response.data], {
      type: 'text/csv;charset=utf-8'
    })

    let filename = `targets_${new Date().toISOString().split('T')[0]}.csv`
    const contentDisposition = response.headers['content-disposition']
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '')
      }
    }

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()

    setTimeout(() => {
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }, 100)

    toast.add({
      severity: 'success',
      summary: 'Exported',
      detail: `${targets.value.length} targets exported`,
      life: 3000
    })
  } catch (error) {
    console.error('Failed to export:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to export targets',
      life: 3000
    })
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped src="../assets/views/target-list-detail.css"></style>
