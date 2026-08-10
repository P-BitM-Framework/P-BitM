<script setup>
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import { formatTimeAgo } from '@/utils/utils.js'
import SentIcon from 'virtual:icons/material-symbols/send-rounded'
import OpenedIcon from 'virtual:icons/material-symbols/mark-email-read-rounded'
import ClickedIcon from 'virtual:icons/material-symbols/ads-click'
import DataIcon from 'virtual:icons/material-symbols/interactive-space'
import PendingIcon from 'virtual:icons/material-symbols/hourglass-empty-rounded'
import ErrorIcon from 'virtual:icons/material-symbols/warning-rounded'

const props = defineProps({
    victims: {
        type: Array,
        required: true
    },
    campaignId: {
        type: String,
        required: true
    },
    campaignType: {
        type: String,
        default: 'full'
    },
    campaignPublicUrl: {
        type: String,
        default: ''
    },
    campaignEntryPath: {
        type: String,
        default: 'continue'
    },
    campaignTrackingParameter: {
        type: String,
        default: ''
    }
})

const emit = defineEmits(['select'])

const toast = useToast()

const searchQuery = ref('')
const statusFilter = ref('all')

const statusOptions = [
    { label: 'All Status', value: 'all' },
    { label: 'Active', value: "true" },
    { label: 'Offline', value: "false" }
]

const filteredVictims = computed(() => {
    let filtered = props.victims

    // Status filter
    if (statusFilter.value !== 'all') {
        filtered = filtered.filter(v => String(v.is_active) === statusFilter.value)
    }

    // Search filter
    if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filtered = filtered.filter(v =>
            v.email?.toLowerCase().includes(query) ||
            v.ip_address?.includes(query)
        )
    }

    return filtered
})

const isStandalone = computed(() => props.campaignType === 'standalone')

function buildTrackingUrl(trackingId) {
    if (!trackingId || !props.campaignPublicUrl) return ''
    const base = props.campaignPublicUrl.endsWith('/')
        ? props.campaignPublicUrl
        : `${props.campaignPublicUrl}/`
    const cleanUrl = props.campaignEntryPath
        ? `${base}${props.campaignEntryPath}`
        : base.replace(/\/$/, '')
    if (props.campaignTrackingParameter) {
        const url = new URL(cleanUrl)
        url.searchParams.set(props.campaignTrackingParameter, trackingId)
        return url.toString()
    }
    return `${cleanUrl}/${trackingId}`
}

async function copyTrackingUrl(trackingId) {
    const url = buildTrackingUrl(trackingId)
    if (!url) return
    try {
        await navigator.clipboard.writeText(url)
        toast.add({
            severity: 'success',
            summary: 'Copied',
            detail: 'Phishing URL copied to clipboard',
            life: 2000
        })
    } catch (_error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to copy phishing URL',
            life: 3000
        })
    }
}

function getStatusSeverity(isActive) {
    return isActive ? 'success' : 'danger'
}

function getStatusLabel(isActive) {
    return isActive ? 'Active' : 'Offline'
}

function getStatusIcon(isActive) {
    return isActive ? 'pi-circle-fill' : 'pi-circle'
}

function getEngagementIcon(status) {
    const icons = {
        'email_sent': SentIcon,
        'email_opened': OpenedIcon,
        'email_link_clicked': ClickedIcon,
        'cookie_captured': DataIcon,
        'form_submitted': DataIcon,
        'data_submitted': DataIcon,
        'pending': PendingIcon,
        'error': ErrorIcon
        // 'compromised': '🎣'
    }
    return icons[status] || null
}

function isRecent(timestamp) {
    if (!timestamp) return false
    const diff = new Date() - new Date(timestamp)
    return diff < 5 * 60 * 1000 // Less than 5 minutes
}

function handleRowClick(event) {
    emit('select', event.data)
}
</script>

<template>
    <Card class="victims-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header">
            <h2 class="section-title">
                <i class="pi pi-users"></i>
                All Targets
                <span class="count-badge">{{ victims.length }}</span>
            </h2>

            <div class="table-controls">
                <IconField iconPosition="left">
                    <InputIcon>
                        <i class="pi pi-search" />
                    </InputIcon>
                    <InputText
                        v-model="searchQuery"
                        placeholder="Search victims..."
                    />
                </IconField>

                <Select
                    v-model="statusFilter"
                    :options="statusOptions"
                    optionLabel="label"
                    optionValue="value"
                    class="status-filter"
                />
            </div>
        </div>

        <DataTable
            :value="filteredVictims"
            stripedRows
            paginator
            :rows="10"
            :rowsPerPageOptions="[10, 25, 50]"
            @row-click="handleRowClick"
            class="data-table data-table--interactive"
        >
            <Column field="is_active" header="Status" style="width: 100px">
                <template #body="{ data }">
                    <Tag
                        :value="getStatusLabel(data.is_active)"
                        :severity="getStatusSeverity(data.is_active)"
                        :icon="`pi ${getStatusIcon(data.is_active)}`"
                    />
                </template>
            </Column>

            <Column header="Victim" style="min-width: 250px">
                <template #body="{ data }">
                    <div class="victim-cell">
                        <div class="victim-info">
                            <strong v-if="data.first_name || data.last_name">
                                {{ data.first_name || '' }} {{ data.last_name || '' }}
                            </strong>
                            <code>{{ data.email || 'Anonymous' }}</code>
                            <span class="victim-meta" v-if="data.ip_address">{{ data.ip_address }}</span>
                            <span class="victim-meta" v-if="data.metadata && data.metadata.Timezone">{{ data.metadata.Timezone || 'Unknown' }}</span>
                        </div>
                    </div>
                </template>
            </Column>

            <Column v-if="isStandalone" header="Tracking Link" style="min-width: 280px">
                <template #body="{ data }">
                    <div class="tracking-cell">
                        <code class="tracking-code">{{ buildTrackingUrl(data.tracking_id) }}</code>
                        <Button
                            icon="pi pi-copy"
                            severity="secondary"
                            text
                            rounded
                            size="small"
                            @click.stop="copyTrackingUrl(data.tracking_id)"
                            v-tooltip.bottom="'Copy URL'"
                        />
                    </div>
                </template>
            </Column>

            <Column v-if="!isStandalone" header="Engagement" style="width: 150px">
                <template #body="{ data }">
                    <div class="engagement-icons">
                        <component
                            :is="getEngagementIcon(data.status)"
                            v-if="data.status"
                            class="icon-badge"
                            role="img"
                            :title="data.status.replace(/_/g, ' ').toUpperCase()"
                            :aria-label="data.status.replace(/_/g, ' ').toUpperCase()"
                        />
                        <!-- <span v-if="data.status === 'email_sent'" class="icon-badge" title="Email sent">✅</span>
                        <span v-if="data.status === 'email_opened'" class="icon-badge" title="Opened">📖</span>
                        <span v-if="data.status === 'email_link_clicked'" class="icon-badge" title="Clicked">🖱️</span>
                        <span v-if="data.status === 'data_collected'" class="icon-badge" title="Data collected">💾</span> -->
                        <!-- <span v-if="data.status === 'compromised'" class="icon-badge" title="Compromised">🎣</span> -->
                    </div>
                </template>
            </Column>

            <Column field="first_seen" header="First Activity" style="width: 140px">
                <template #body="{ data }">
                    <span class="time-ago" :class="{'recent': isRecent(data.first_seen)}">
                        {{ formatTimeAgo(data.first_seen) }}
                    </span>
                </template>
            </Column>

            <Column field="last_seen" header="Last Activity" style="width: 140px">
                <template #body="{ data }">
                    <span class="time-ago" :class="{'recent': isRecent(data.last_seen)}">
                        {{ formatTimeAgo(data.last_seen) }}
                    </span>
                </template>
            </Column>

            <Column style="width: 120px" headerClass="sticky-actions" bodyClass="sticky-actions">
                <template #body="{ data }">
                    <Button
                        :label="data.is_active ? 'Monitor' : 'View'"
                        :icon="data.is_active ? 'pi pi-external-link' : 'pi pi-eye'"
                        iconPos="right"
                        size="small"
                        :severity="data.is_active ? 'success' : 'secondary'"
                        text
                        @click="$emit('select', data)"
                    />
                </template>
            </Column>

            <template #empty>
                <div class="empty-state">
                    <i class="pi pi-inbox"></i>
                    <p>No victims found</p>
                </div>
            </template>
        </DataTable>
    </template>
    </Card>
</template>

<style scoped>
/* .victims-table {
    background-color: var(--color-background-soft);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 1.5rem 1.5rem 0 1.5rem;
} */

/* .table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 1rem;
} */

/* .section-title {
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
} */

code {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.875rem;
}

.victims-table-card :deep(.p-card-body) {
    padding: 0;
}

.victims-table-card :deep(.p-card-content) {
    padding: 0;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
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
}

.search-input {
    width: 250px;
    margin-left: 10px;
}

.status-filter {
    width: 150px;
}

/* Table Styling */
/* .data-table {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

.data-table :deep(.p-datatable-tbody > tr) {
    cursor: pointer;
    transition: background-color 0.2s;
}

.data-table :deep(.p-datatable-tbody > tr:hover) {
    background-color: var(--color-background-mute) !important;
} */

/* Victim Cell */
.victim-cell {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.victim-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.tracking-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.tracking-code {
    display: inline-block;
    max-width: 240px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    background: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
}

.victim-info strong {
    color: var(--color-heading);
    font-size: 0.9rem;
}

.victim-meta {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

/* Engagement Icons */
.engagement-icons {
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
}

.icon-badge {
    width: 1.1rem;
    height: 1.1rem;
    font-size: 1.1rem;
    color: var(--color-text-mute);
}

/* Data Stats */
.data-stats {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.data-stats .stat {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.85rem;
    color: var(--color-text);
}

.data-stats .stat i {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

.session-duration {
    color: var(--color-text-mute);
    font-size: 0.75rem;
}

/* Time Ago */
.time-ago {
    font-size: 0.875rem;
    color: var(--color-text-mute);
}

.time-ago.recent {
    color: var(--success);
    font-weight: 600;
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

.empty-state p {
    margin: 0;
    font-size: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
    .table-header {
        flex-direction: column;
        align-items: stretch;
    }

    .table-controls {
        flex-direction: column;
    }

    .search-input,
    .status-filter {
        width: 100%;
    }
}
</style>
