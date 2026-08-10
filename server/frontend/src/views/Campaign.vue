<script setup>
import { ref, onMounted, computed, defineAsyncComponent, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import CampaignCard from '@/components/campaign/CampaignCard.vue'
import CampaignListItem from '@/components/campaign/CampaignListItem.vue'
import DeleteCampaignDialog from '@/components/campaign/DeleteCampaignDialog.vue'
import LoaderDialog from '@/components/campaign/LoaderDialog.vue'
import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import PageHeader from '@/components/default/PageHeader.vue'
import EmptyState from '@/components/default/EmptyState.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const NewCampaignCard = defineAsyncComponent(() => import('@/components/campaign/NewCampaignCard.vue'))

const router = useRouter()
const toast = useToast()


// State
const campaigns = ref([])
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const loadError = ref(null)
const refreshErrorNotified = ref(false)
const campaignDialogVisible = ref(false)
const selectedCampaign = ref(null)
const confirmDeleteVisible = ref(false)
const deleting = ref(false)
const deletingLoaderVisible = ref(false)

// Persist the selected filters and layout locally.
const savedViewMode = localStorage.getItem('campaigns_view_mode') || 'grid'
const savedStatusFilter = localStorage.getItem('campaigns_status_filter') || 'all'

const searchQuery = ref('')
const selectedStatus = ref(savedStatusFilter)
const viewMode = ref(savedViewMode)

watch(viewMode, (newValue) => {
    localStorage.setItem('campaigns_view_mode', newValue)
})

watch(selectedStatus, (newValue) => {
    localStorage.setItem('campaigns_status_filter', newValue)
})

// Context Menu
const contextMenu = ref(null)
const contextMenuItems = ref([
    {
        label: 'Delete campaign',
        icon: 'pi pi-trash',
        command: () => confirmDeleteVisible.value = true,
        class: 'delete-menu-item'
    }
])

// Filter Options
const statusOptions = ref([
    { label: 'All campaigns', value: 'all', icon: 'pi pi-list' },
    { label: 'Active', value: 'active', icon: 'pi pi-play-circle' },
    { label: 'Scheduled', value: 'scheduled', icon: 'pi pi-clock' },
    { label: 'Completed', value: 'completed', icon: 'pi pi-check-circle' }
])

// View Options
const viewOptions = ref([
    { label: 'Grid', value: 'grid', icon: 'pi pi-th-large' },
    { label: 'List', value: 'list', icon: 'pi pi-list' }
])

// Computed - Base filters
const activeCampaigns = computed(() =>
    campaigns.value.filter(c => c.status === 'active')
)

const completedCampaigns = computed(() =>
    campaigns.value.filter(c => c.status === 'completed')
)

const scheduledCampaigns = computed(() =>
    campaigns.value.filter(c => c.status === 'scheduled')
)

// Computed - Filtered campaigns
const filteredCampaigns = computed(() => {
    let filtered = campaigns.value

    // Filter by status
    if (selectedStatus.value !== 'all') {
        filtered = filtered.filter(c => c.status === selectedStatus.value)
    }

    // Filter by search query
    if (searchQuery.value.trim()) {
        const query = searchQuery.value.toLowerCase().trim()
        filtered = filtered.filter(c =>
            c.name.toLowerCase().includes(query) ||
            c.description?.toLowerCase().includes(query)
        )
    }

    return filtered
})

// Computed - Grouped filtered campaigns (for sections)
const filteredActiveCampaigns = computed(() =>
    filteredCampaigns.value.filter(c => c.status === 'active')
)

const filteredScheduledCampaigns = computed(() =>
    filteredCampaigns.value.filter(c => c.status === 'scheduled')
)

const filteredCompletedCampaigns = computed(() =>
    filteredCampaigns.value.filter(c => c.status === 'completed')
)

// Computed - Counts for dropdown
const statusCounts = computed(() => ({
    all: campaigns.value.length,
    active: activeCampaigns.value.length,
    scheduled: scheduledCampaigns.value.length,
    completed: completedCampaigns.value.length
}))

// Computed - Show sections?
const showSections = computed(() => {
    return selectedStatus.value === 'all' && !searchQuery.value.trim()
})

function openCampaign(campaign) {
    router.push({
        name: 'campaign',
        params: { campaignId: campaign.id }
    })
}

function openNewCampaignDialog() {
    campaignDialogVisible.value = true
}

function onCardRightClick(event, campaign) {
    event.preventDefault()
    selectedCampaign.value = campaign
    contextMenu.value.show(event)
}

async function deleteCampaign(campaign) {
    if (!campaign) return

    try {
        await backendService.deleteCampaign(campaign.id)
        toast.add({
            severity: 'success',
            summary: 'Deleted',
            detail: `Campaign "${campaign.name}" deleted`,
            life: 2000
        })
        await fetchCampaigns()
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to delete campaign: ' + error.message,
            life: 3000
        })
    }
}

async function handleDeleteCampaign() {
    if (deleting.value) return

    deleting.value = true
    confirmDeleteVisible.value = false
    deletingLoaderVisible.value = true

    await deleteCampaign(selectedCampaign.value)

    deleting.value = false
    deletingLoaderVisible.value = false
}

function getStatusLabel(status) {
    const option = statusOptions.value.find(opt => opt.value === status)
    return option ? option.label : 'All campaigns'
}

function getStatusOption(status) {
    return statusOptions.value.find(option => option.value === status) || statusOptions.value[0]
}

onMounted(() => {
    fetchCampaigns(true)
})

useVisibilityPolling(
    (signal) => fetchCampaigns(false, signal),
    {
        intervalMs: 30000,
        enabled: () => !loading.value,
        immediate: false
    }
)

async function fetchCampaigns(showLoading = true, signal) {
    if (showLoading) {
        loading.value = true
        loadError.value = null
    }
    try {
        const response = await backendService.getCampaigns({ signal })
        campaigns.value = Array.isArray(response) ? response : []
        loadError.value = null
        refreshErrorNotified.value = false
    } catch (error) {
        if (error?.name === 'AbortError') return
        if (campaigns.value.length === 0) {
            loadError.value = error.message || 'Failed to fetch campaigns'
        }
        if (showLoading || !refreshErrorNotified.value) {
            toast.add({
                severity: 'error',
                summary: 'Refresh failed',
                detail: 'Failed to fetch campaigns: ' + error.message,
                life: 3000
            })
            refreshErrorNotified.value = true
        }
    } finally {
        if (showLoading) {
            loading.value = false
        }
    }
}

const isCreatingCampaign = ref(false)

async function handleCampaignCreated() {
    await fetchCampaigns(false)

    campaignDialogVisible.value = false

    toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Campaign created successfully',
        life: 2000
    })
}
</script>

<template>
    <ContextMenu ref="contextMenu" :model="contextMenuItems" />

    <div class="campaigns-page app-page">
        <DelayedContent :loading="loading" :show-indicator="showLoading">
        <PageHeader title="Campaigns" subtitle="Manage and monitor your campaigns">
            <template #actions>
                <Button
                    label="New Campaign"
                    icon="pi pi-plus"
                    @click="openNewCampaignDialog"
                    class="new-campaign-btn"
                />
            </template>
        </PageHeader>

        <!-- Toolbar -->
        <div
            v-if="campaigns.length > 0"
            class="campaigns-toolbar app-toolbar"
            :aria-busy="loading"
        >
            <!-- Search -->
                <IconField iconPosition="left">
                    <InputIcon>
                        <i class="pi pi-search" />
                    </InputIcon>
                    <InputText
                        v-model="searchQuery"
                        placeholder="Search campaign..."
                        :disabled="loading"
                    />
              </IconField>

            <div class="toolbar-right">

                <!-- Status Filter -->
                <Select
                    v-model="selectedStatus"
                    :options="statusOptions"
                    optionLabel="label"
                    optionValue="value"
                    class="status-filter"
                    :disabled="loading"
                >
                    <template #value="slotProps">
                        <div class="filter-value">
                            <span class="filter-label">
                                <i
                                    :class="[
                                        getStatusOption(slotProps.value).icon,
                                        'status-filter-icon',
                                        `status-filter-icon--${getStatusOption(slotProps.value).value}`
                                    ]"
                                ></i>
                                <span>{{ getStatusLabel(slotProps.value) }}</span>
                            </span>
                            <span class="count-badge">{{ statusCounts[slotProps.value] }}</span>
                        </div>
                    </template>
                    <template #option="slotProps">
                        <div class="filter-option">
                            <span class="filter-label">
                                <i
                                    :class="[
                                        slotProps.option.icon,
                                        'status-filter-icon',
                                        `status-filter-icon--${slotProps.option.value}`
                                    ]"
                                ></i>
                                <span>{{ slotProps.option.label }}</span>
                            </span>
                            <span class="option-count">{{ statusCounts[slotProps.option.value] }}</span>
                        </div>
                    </template>
                </Select>

                <!-- View Toggle -->
                <SelectButton
                    v-model="viewMode"
                    :options="viewOptions"
                    optionValue="value"
                    class="view-toggle"
                    :allowEmpty="false"
                    :disabled="loading"
                >
                    <template #option="slotProps">
                        <i :class="slotProps.option.icon"></i>
                    </template>
                </SelectButton>
            </div>
        </div>

        <!-- Error State -->
        <EmptyState
            v-if="loadError"
            icon="pi pi-exclamation-circle"
            title="Campaigns could not be loaded"
            :description="loadError"
            tone="danger"
        >
            <template #actions>
                <Button label="Try Again" icon="pi pi-refresh" @click="fetchCampaigns(true)" />
            </template>
        </EmptyState>

        <!-- Empty State -->
        <EmptyState
            v-else-if="campaigns.length === 0"
            title="No campaigns yet"
            description="Create your first campaign to get started"
        >
            <template #actions>
                <Button
                    label="Create Campaign"
                    icon="pi pi-plus"
                    @click="openNewCampaignDialog"
                    size="large"
                />
            </template>
        </EmptyState>

        <!-- No Results State -->
        <EmptyState
            v-else-if="filteredCampaigns.length === 0"
            icon="pi pi-search"
            title="No campaigns found"
            description="Try adjusting your search or filters"
        >
            <template #actions>
                <Button
                    label="Clear filters"
                    icon="pi pi-times"
                    @click="searchQuery = ''; selectedStatus = 'all'"
                    outlined
                />
            </template>
        </EmptyState>

        <!-- Campaigns Content - SECTIONED VIEW -->
        <div v-else-if="showSections" class="campaigns-content">
            <!-- Active Campaigns -->
            <section v-if="filteredActiveCampaigns.length > 0" class="campaigns-section">
                <div class="section-header">
                    <h2>
                        <i class="pi pi-circle-fill status-active"></i>
                        Active Now
                        <span class="count-badge">{{ filteredActiveCampaigns.length }}</span>
                    </h2>
                </div>
                <TransitionGroup v-if="viewMode === 'grid'" tag="div" name="list-fade" class="campaigns-grid">
                    <CampaignCard
                        v-for="campaign in filteredActiveCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
                <TransitionGroup v-else tag="div" name="list-fade" class="campaigns-list">
                    <CampaignListItem
                        v-for="campaign in filteredActiveCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
            </section>

            <!-- Scheduled Campaigns -->
            <section v-if="filteredScheduledCampaigns.length > 0" class="campaigns-section">
                <div class="section-header">
                    <h2>
                        <i class="pi pi-clock status-scheduled"></i>
                        Scheduled
                        <span class="count-badge">{{ filteredScheduledCampaigns.length }}</span>
                    </h2>
                </div>
                <TransitionGroup v-if="viewMode === 'grid'" tag="div" name="list-fade" class="campaigns-grid">
                    <CampaignCard
                        v-for="campaign in filteredScheduledCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
                <TransitionGroup v-else tag="div" name="list-fade" class="campaigns-list">
                    <CampaignListItem
                        v-for="campaign in filteredScheduledCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
            </section>

            <!-- Completed Campaigns -->
            <section v-if="filteredCompletedCampaigns.length > 0" class="campaigns-section">
                <div class="section-header">
                    <h2>
                        <i class="pi pi-check-circle status-completed"></i>
                        Completed
                        <span class="count-badge">{{ filteredCompletedCampaigns.length }}</span>
                    </h2>
                </div>
                <TransitionGroup v-if="viewMode === 'grid'" tag="div" name="list-fade" class="campaigns-grid">
                    <CampaignCard
                        v-for="campaign in filteredCompletedCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
                <TransitionGroup v-else tag="div" name="list-fade" class="campaigns-list">
                    <CampaignListItem
                        v-for="campaign in filteredCompletedCampaigns"
                        :key="campaign.id"
                        :campaign="campaign"
                        @select="openCampaign"
                        @contextmenu="onCardRightClick"
                    />
                </TransitionGroup>
            </section>
        </div>

        <!-- Campaigns Content - FLAT VIEW (when filtered or searched) -->
        <div v-else class="campaigns-content-flat">
            <TransitionGroup v-if="viewMode === 'grid'" tag="div" name="list-fade" class="campaigns-grid">
                <CampaignCard
                    v-for="campaign in filteredCampaigns"
                    :key="campaign.id"
                    :campaign="campaign"
                    @select="openCampaign"
                    @contextmenu="onCardRightClick"
                />
            </TransitionGroup>
            <TransitionGroup v-else tag="div" name="list-fade" class="campaigns-list">
                <CampaignListItem
                    v-for="campaign in filteredCampaigns"
                    :key="campaign.id"
                    :campaign="campaign"
                    @select="openCampaign"
                    @contextmenu="onCardRightClick"
                />
            </TransitionGroup>
        </div>
        </DelayedContent>

        <!-- Dialogs -->
        <Dialog
            v-model:visible="campaignDialogVisible"
            :modal="true"
            :draggable="false"
            :closable="!isCreatingCampaign"
            header="New Campaign"
            :style="{ width: '900px' }"
        >
            <Suspense>
                <NewCampaignCard
                  v-if="campaignDialogVisible"
                  @campaign-created="handleCampaignCreated"
                  @creating-changed="isCreatingCampaign = $event"
                  @cancel="campaignDialogVisible = false"
                />
                <template #fallback>
                    <div class="dialog-loading">
                        <i class="pi pi-spin pi-spinner"></i>
                        <span>Loading campaign builder...</span>
                    </div>
                </template>
            </Suspense>
        </Dialog>

        <DeleteCampaignDialog
            :visible="confirmDeleteVisible"
            :campaignName="selectedCampaign?.name"
            :deleting="deleting"
            @update:visible="confirmDeleteVisible = $event"
            @cancel="confirmDeleteVisible = false"
            @confirm="handleDeleteCampaign"
        />

        <LoaderDialog
            :visible="deletingLoaderVisible"
            message="Deleting campaign and related containers..."
        />
    </div>
</template>

<style scoped>
.campaigns-page {
    min-height: 100vh;
    padding: var(--page-padding);
    background-color: var(--color-background);
}

.new-campaign-btn {
    min-width: 160px;
}

/* ===================================================================
   TOOLBAR
   =================================================================== */

.campaigns-toolbar {
    display: flex;
    gap: 1rem;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    background: var(--color-background-soft);
    /* border: 1px solid var(--color-border); */
    border-radius: 8px;
    margin-bottom: 2rem;
}

.toolbar-right {
    display: flex;
    gap: 1rem;
    align-items: center;
}

/* Search */
.search-wrapper {
    display: flex;
    flex: 1;
    align-items: center;
    flex-direction: row;
    max-width: 400px;
}

.search-input {
    width: 100%;
}

/* Status Filter Select */
.status-filter {
    min-width: 200px;
}

.filter-value {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
}

.filter-value .count-badge {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-mute);
    background: var(--color-background);
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    min-width: 1.5rem;
    text-align: center;
}

.filter-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
}

.filter-label {
    display: inline-flex;
    align-items: center;
    min-width: 0;
    gap: 0.625rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    font-weight: 550;
}

.status-filter-icon {
    width: 1rem;
    color: var(--text-muted);
    font-size: 0.9rem;
    text-align: center;
}

.status-filter-icon--active {
    color: var(--success);
}

.status-filter-icon--scheduled {
    color: var(--warning);
}

.status-filter-icon--completed {
    color: var(--text-secondary);
}

.option-count {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-mute);
    background: var(--color-background-soft);
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    min-width: 1.5rem;
    text-align: center;
}

/* View Toggle */
.view-toggle {
    margin-left: auto;
}

:deep(.view-toggle .p-button) {
    padding: 0.5rem 0.75rem;
}

:deep(.view-toggle .p-button i) {
    font-size: 1rem;
}

/* ===================================================================
   EMPTY STATES
   =================================================================== */

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 5rem 2rem;
    text-align: center;
    gap: 1rem;
}

.dialog-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    min-height: 320px;
    color: var(--color-text-mute);
}

.empty-icon {
    font-size: 4rem;
    color: var(--color-text-mute);
    opacity: 0.5;
    margin-bottom: 1rem;
}

.empty-state h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.empty-state p {
    color: var(--color-text-mute);
    margin: 0 0 1.5rem 0;
    font-size: 1rem;
}

/* ===================================================================
   CAMPAIGNS SECTIONS
   =================================================================== */

.campaigns-content {
    display: flex;
    flex-direction: column;
    gap: 2.5rem;
}

.campaigns-content-flat {
    margin-top: 0;
}

.section-header {
    margin-bottom: 1.25rem;
}

.section-header h2 {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.section-header i {
    font-size: 1rem;
}

.status-active {
    color: var(--success);
}

.status-scheduled {
    color: var(--warning);
}

.status-completed {
    color: var(--text-muted);
}

.count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.5rem;
    height: 1.5rem;
    padding: 0 0.5rem;
    background-color: var(--color-background-mute);
    /* border: 1px solid var(--color-border); */
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-mute);
}

/* ===================================================================
   GRID & LIST VIEWS
   =================================================================== */

.campaigns-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1.5rem;
}

.campaigns-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

/* ===================================================================
   RESPONSIVE
   =================================================================== */

@media (max-width: 1024px) {
    .campaigns-toolbar {
        flex-wrap: wrap;
    }

    .search-wrapper {
        flex: 1 1 100%;
        max-width: 100%;
        order: 1;
    }

    .status-filter {
        flex: 1;
        order: 2;
    }

    .view-toggle {
        margin-left: 0;
        order: 3;
    }
}

@media (max-width: 768px) {
    .campaigns-page {
        padding: 1rem;
    }

    .page-header {
        flex-direction: column;
        gap: 1rem;
        align-items: stretch;
    }

    .new-campaign-btn {
        width: 100%;
    }

    .campaigns-toolbar {
        flex-direction: column;
        align-items: stretch;
    }

    .search-wrapper {
        max-width: 100%;
    }

    .status-filter,
    .view-toggle {
        width: 100%;
    }

    .campaigns-grid {
        grid-template-columns: 1fr;
    }

    .header-content h1 {
        font-size: 1.5rem;
    }
}
</style>
