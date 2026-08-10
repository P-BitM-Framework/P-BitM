<template>
    <div class="target-lists-view app-page">
        <DelayedContent :loading="loading" :show-indicator="showLoading">
        <PageHeader title="Target Lists" subtitle="Manage and organize campaign targets">
            <template #actions>
                <Button label="New List" icon="pi pi-plus" @click="showAddDialog = true" />
            </template>
        </PageHeader>

        <!-- Stats Cards -->
        <div class="stats-row metrics-grid">
            <Card class="stat-card metric-card">
                <template #content>
                    <div class="stat-content">
                        <i class="pi pi-users"></i>
                        <div class="stat-text">
                            <div class="stat-value">{{ targetLists.length }}</div>
                            <div class="stat-label">Lists</div>
                        </div>
                    </div>
                </template>
            </Card>

            <Card class="stat-card metric-card">
                <template #content>
                    <div class="stat-content">
                        <i class="pi pi-users"></i>
                        <div class="stat-text">
                            <div class="stat-value">{{ totalTargets }}</div>
                            <div class="stat-label">Total Targets</div>
                        </div>
                    </div>
                </template>
            </Card>

            <Card class="stat-card metric-card">
                <template #content>
                    <div class="stat-content">
                        <i class="pi pi-chart-line"></i>
                        <div class="stat-text">
                            <div class="stat-value">{{ averageListSize }}</div>
                            <div class="stat-label">Avg per List</div>
                        </div>
                    </div>
                </template>
            </Card>
        </div>

        <!-- Target Lists Table -->
        <Card class="target-lists-card app-table-card">
            <template #content>
                <div class="table-header app-table-header">
                    <h2 class="section-title app-section-title">
                        <i class="pi pi-users"></i>
                        All Target Lists
                        <span class="count-badge">{{ targetLists.length }}</span>
                    </h2>

                    <div class="table-controls app-table-controls">
                        <IconField iconPosition="left">
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText
                                v-model="filters['global'].value"
                                placeholder="Search lists..."
                                class="search-input"
                            />
                        </IconField>

                        <Button
                            icon="pi pi-refresh"
                            severity="secondary"
                            text
                            rounded
                            @click="fetchTargetLists"
                            :loading="showLoading"
                            v-tooltip.bottom="'Refresh'"
                        />
                    </div>
                </div>

                <DataTable
                    :value="targetLists"
                    :loading="showLoading"
                    :globalFilterFields="['name', 'description']"
                    v-model:filters="filters"
                    paginator
                    :rows="25"
                    :rowsPerPageOptions="[10, 25, 50, 100]"
                    @row-click="onRowClick"
                    class="data-table data-table--interactive"
                >
                    <template #empty>
                        <div class="empty-state">
                            <i class="pi pi-inbox"></i>
                            <p>No target lists yet</p>
                            <Button
                                label="Create Target List"
                                icon="pi pi-plus"
                                @click="showAddDialog = true"
                                size="small"
                                class="mt-2"
                            />
                        </div>
                    </template>

                    <!-- Name Column -->
                    <Column field="name" header="Name" sortable style="min-width: 300px">
                        <template #body="{ data }">
                            <div class="list-cell">
                                <div class="list-icon">
                                    <i class="pi pi-users"></i>
                                </div>
                                <div class="list-info">
                                    <strong>{{ data.name }}</strong>
                                    <span v-if="data.description" class="list-meta">{{ data.description }}</span>
                                </div>
                            </div>
                        </template>
                    </Column>

                    <!-- Company -->
                    <Column field="company" header="Company" sortable style="min-width: 160px">
                        <template #body="{ data }">
                            <span class="list-meta">{{ data.company || '—' }}</span>
                        </template>
                    </Column>

                    <!-- Targets Count -->
                    <Column field="total_targets" header="Targets" sortable style="width: 140px">
                        <template #body="{ data }">
                            <Tag
                                :value="String(data.total_targets || 0)"
                                :severity="data.total_targets > 0 ? 'success' : 'secondary'"
                                :icon="data.total_targets > 0 ? 'pi pi-users' : 'pi pi-user'"
                            />
                        </template>
                    </Column>

                    <!-- Times Used -->
                    <Column field="times_used" header="Campaigns" sortable style="width: 140px">
                        <template #body="{ data }">
                            <div class="usage-cell">
                                <span class="usage-badge">
                                    <i class="pi pi-bolt"></i>
                                    {{ data.usage_count || 0 }}
                                </span>
                            </div>
                        </template>
                    </Column>

                    <!-- Created Date -->
                    <Column field="created_at" header="Created" sortable style="width: 160px">
                        <template #body="{ data }">
                            <span class="time-ago">
                                <i class="pi pi-calendar"></i>
                                {{ formatDateLocal(data.created_at) }}
                            </span>
                        </template>
                    </Column>

                    <!-- Actions -->
                    <Column header="" style="width: 140px" headerClass="sticky-actions" bodyClass="sticky-actions">
                        <template #body="{ data }">
                            <div class="action-buttons">
                                <Button
                                    icon="pi pi-eye"
                                    iconPos="right"
                                    size="small"
                                    severity="secondary"
                                    text
                                    @click.stop="viewList(data.id)"
                                />
                                <Button
                                    icon="pi pi-trash"
                                    size="small"
                                    severity="danger"
                                    text
                                    rounded
                                    v-tooltip.top="'Delete'"
                                    @click.stop="confirmDelete(data)"
                                />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>
        </DelayedContent>

        <!-- New List Dialog -->
        <Dialog
            v-model:visible="showAddDialog"
            modal
            header="New Target List"
            :style="{ width: '600px' }"
            :draggable="false"
            @hide="resetListForm"
        >
            <div class="form-grid">
                <div class="field">
                    <label for="name">Name <span class="required">*</span></label>
                    <InputText
                        id="name"
                        v-model="newList.name"
                        class="w-full"
                        placeholder="John"
                        :invalid="submitted && !newList.name"
                    />
                    <small v-if="submitted && !newList.name" class="p-error">Name is required</small>
                </div>

                <div class="field">
                    <label for="description">Description</label>
                    <InputText
                    id="description"
                    v-model="newList.description"
                    class="w-full"
                    placeholder="Doe"
                    />
                </div>

                <div class="field">
                    <label for="company">Company</label>
                    <InputText
                    id="company"
                    v-model="newList.company"
                    class="w-full"
                    placeholder="Acme Corp"
                    />
                </div>
            </div>

            <template #footer>
                <Button label="Cancel" severity="secondary" text @click="showAddDialog = false" />
                <Button
                    label="Create List"
                    icon="pi pi-check"
                    :disabled="!newList.name.trim()"
                    :loading="saving"
                    @click="saveList"
                />
            </template>
        </Dialog>
        <DeleteResourceDialog
            v-model:visible="showDeleteDialog"
            header="Delete Target List"
            :subject="listToDelete?.name"
            confirm-label="Delete List"
            :loading="deleting"
            width="500px"
            @confirm="deleteList"
        >
            <p>
                This will permanently delete this list and all
                <strong>{{ listToDelete?.total_targets || 0 }} targets</strong> in it.
            </p>

            <Message severity="warn" :closable="false">
                <span>
                    <strong>Warning:</strong>
                    This list has been used {{ listToDelete?.usage_count || 0 }} times in campaigns.
                </span>
            </Message>
        </DeleteResourceDialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import { backendService } from '@/services/backend'
import { formatDateLocal } from '@/utils/utils'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DeleteResourceDialog from '@/components/default/DeleteResourceDialog.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const router = useRouter()
const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const deleting = ref(false)
const targetLists = ref([])
const showDeleteDialog = ref(false)
const listToDelete = ref(null)
const saving = ref(false)
const submitted = ref(false)

const newList = ref({
    name: '',
    description: '',
    company: ''
})
const showAddDialog = ref(false)

const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

// Computed
const totalTargets = computed(() => {
    return targetLists.value.reduce((sum, list) => sum + (list.total_targets || 0), 0)
})

const averageListSize = computed(() => {
    if (targetLists.value.length === 0) return 0
    return Math.round(totalTargets.value / targetLists.value.length)
})

// Methods
const fetchTargetLists = async () => {
    loading.value = true
    try {
        const data = await backendService.getTargetLists()
        targetLists.value = data.target_lists || []
    } catch (error) {
        console.error('Failed to fetch target lists:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load target lists',
            life: 3000
        })
    } finally {
        loading.value = false
    }
}

const onRowClick = (event) => {
    viewList(event.data.id)
}

const resetListForm = () => {
    newList.value = {
        name: '',
        description: '',
        company: ''
    }
}

const saveList = async () => {
    if (!newList.value.name.trim()) {
        toast.add({
            severity: 'warn',
            summary: 'Validation Error',
            detail: 'List name is required',
            life: 3000
        })
        return
    }

    saving.value = true
    try {
        const createdList = await backendService.createTargetList(newList.value)
        toast.add({
            severity: 'success',
            summary: 'Created',
            detail: `Target list "${createdList.name}" created successfully`,
            life: 3000
        })
        showAddDialog.value = false
        await fetchTargetLists()
        router.push({ name: 'target-list', params: { listId: createdList.id } })
    } catch (error) {
        console.error('Failed to create target list:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to create target list',
            life: 3000
        })
    } finally {
        saving.value = false
        submitted.value = false
  }
}

const viewList = (id) => {
    router.push({ name: 'target-list', params: { listId: id } })
}

const confirmDelete = (list) => {
    listToDelete.value = list
    showDeleteDialog.value = true
}

const deleteList = async () => {
    if (!listToDelete.value) return

    deleting.value = true
    try {
        await backendService.deleteTargetList(listToDelete.value.id)
        toast.add({
            severity: 'success',
            summary: 'Deleted',
            detail: `"${listToDelete.value.name}" deleted successfully`,
            life: 3000
        })
        showDeleteDialog.value = false
        listToDelete.value = null
        await fetchTargetLists()
    } catch (error) {
        console.error('Failed to delete target list:', error)
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

onMounted(() => {
    fetchTargetLists()
})
</script>

<style scoped>
/* ==================== LAYOUT ==================== */
.target-lists-view {
    padding: var(--page-padding);
    max-width: var(--content-max-width);
    margin: 0 auto;
    min-height: 100vh;
}

/* ==================== STATS CARDS ==================== */
.stats-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.stat-card {
    transition: border-color var(--duration-normal) var(--ease-standard);
}

.stat-card:hover {
    border-color: var(--border-strong);
}

.stat-card :deep(.p-card-body) {
    padding: 1.5rem;
}

.stat-card :deep(.p-card-content) {
    padding: 0;
}

.stat-content {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.stat-content i {
    font-size: 2.5rem;
    color: var(--color-text-mute);
}

.stat-text {
    flex: 1;
}

.stat-value {
    font-size: 1.875rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.375rem;
    color: var(--color-heading);
}

.stat-label {
    color: var(--color-text-mute);
    font-size: 0.875rem;
    font-weight: 500;
}

/* ==================== TABLE CARD ==================== */
.target-lists-card :deep(.p-card-body) {
    padding: 0;
}

.target-lists-card :deep(.p-card-content) {
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

/* ==================== LIST CELL ==================== */
.list-cell {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.list-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    border-radius: var(--radius-sm);
    flex-shrink: 0;
    transition: var(--transition-interactive);
}

.data-table :deep(tr:hover) .list-icon {
    background: transparent;
    transform: none;
}

.list-icon i {
    font-size: 1.25rem;
    color: var(--color-text);
}

.list-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.list-info strong {
    color: var(--color-heading);
    font-size: 0.9rem;
}

.list-meta {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

/* ==================== USAGE CELL ==================== */
.usage-cell {
    display: flex;
    align-items: center;
}

.usage-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.625rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text);
    transition: var(--transition-interactive);
}

.data-table :deep(tr:hover) .usage-badge {
    background-color: var(--color-background-soft);
}

.usage-badge i {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

/* ==================== TIME AGO ==================== */
.time-ago {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.875rem;
    color: var(--color-text-mute);
}

.time-ago i {
    font-size: 0.75rem;
}

/* ==================== ACTION BUTTONS ==================== */
.action-buttons {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    justify-content: flex-end;
}

/* ==================== EMPTY STATE ==================== */
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

.empty-state p {
    margin: 0;
    font-size: 1rem;
}

/* ==================== FORMS ==================== */
.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  margin-top: 1rem;
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

/* ==================== RESPONSIVE ==================== */
@media (max-width: 768px) {
    .target-lists-view {
        padding: 1rem;
    }

    .page-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .stats-row {
        grid-template-columns: 1fr;
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
