<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { formatDateLocal, getCampaignStatusConfig } from '@/utils/utils.js'

const props = defineProps({
    campaign: {
        type: Object,
        required: true
    },
    runtimeAction: {
        type: String,
        default: null
    }
})

const emit = defineEmits(['back', 'pause', 'resume', 'stop'])

const statusConfig = computed(() => getCampaignStatusConfig(props.campaign.status))

const createdDateTime = computed(() => {
    return formatDateLocal(props.campaign.created_at, false)
})

const isStandalone = computed(() => props.campaign?.campaign_type === 'standalone')

const scheduledStart = computed(() => {
    return props.campaign.scheduled_start
        ? formatDateLocal(props.campaign.scheduled_start, false)
        : 'Not scheduled'
})

const scheduledEnd = computed(() => {
    return props.campaign.scheduled_end
        ? formatDateLocal(props.campaign.scheduled_end, false)
        : 'Not scheduled'
})
</script>

<template>
    <div class="campaign-header">
        <div class="header-content">
            <div class="title-section">
                <Button
                    icon="pi pi-arrow-left"
                    text
                    rounded
                    @click="emit('back')"
                    class="back-btn"
                />
                <div class="title-group">
                    <Tag
                        :value="statusConfig.label"
                        :severity="statusConfig.severity"
                        :icon="statusConfig.icon"
                    />
                    <h1>{{ campaign.name }}</h1>
                </div>
            </div>

            <div class="actions">
                <Button v-if="campaign.status === 'active'"
                    label="Pause Campaign"
                    icon="pi pi-pause"
                    severity="secondary"
                    outlined
                    :loading="runtimeAction === 'pause'"
                    :disabled="Boolean(runtimeAction)"
                    @click="emit('pause')"
                />
                <Button v-if="campaign.status === 'paused'"
                    label="Resume Campaign"
                    icon="pi pi-play"
                    severity="success"
                    outlined
                    :loading="runtimeAction === 'resume'"
                    :disabled="Boolean(runtimeAction)"
                    @click="emit('resume')"
                />
                <Button v-if="campaign.status === 'active'"
                    label="Stop Campaign"
                    icon="pi pi-stop"
                    severity="danger"
                    outlined
                    :disabled="Boolean(runtimeAction)"
                    @click="emit('stop')"
                />
                <Button v-else-if="campaign.status === 'paused'"
                    label="Stop Campaign"
                    icon="pi pi-stop"
                    severity="danger"
                    outlined
                    :disabled="Boolean(runtimeAction)"
                    @click="emit('stop')"
                />
            </div>
        </div>

        <div class="header-details">
            <section class="detail-group">
                <h2>Campaign details</h2>
                <div class="detail-grid">
                    <div class="info-item" v-if="!isStandalone">
                        <i class="pi pi-envelope"></i>
                        <span class="info-copy"><small>From</small><strong>{{ campaign.from_email || 'N/A' }}</strong></span>
                    </div>
                    <div class="info-item">
                        <i class="pi pi-calendar-plus"></i>
                        <span class="info-copy"><small>Created</small><strong>{{ createdDateTime }}</strong></span>
                    </div>
                    <div v-if="campaign.status === 'completed' && campaign.completed_at" class="info-item">
                        <i class="pi pi-check-circle"></i>
                        <span class="info-copy"><small>Actually ended</small><strong>{{ formatDateLocal(campaign.completed_at, false) }}</strong></span>
                    </div>
                </div>
            </section>

            <section v-if="!isStandalone" class="detail-group schedule-group">
                <h2>Email delivery window</h2>
                <div class="detail-grid schedule-grid">
                    <div class="info-item schedule-start">
                        <i class="pi pi-play-circle"></i>
                        <span class="info-copy"><small>Email sending starts</small><strong>{{ scheduledStart }}</strong></span>
                    </div>
                    <div class="info-item schedule-end">
                        <i class="pi pi-stop-circle"></i>
                        <span class="info-copy"><small>Email sending ends</small><strong>{{ scheduledEnd }}</strong></span>
                    </div>
                </div>
            </section>
        </div>
    </div>
</template>

<style scoped>
.campaign-header {
    background-color: var(--color-background-soft);
    border-radius: 8px;
    padding: 1.5rem;
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
}

.title-section {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.back-btn {
    margin-top: 0.125rem;
}

.title-group {
    display: flex;
    flex-direction: row;
    gap: 0.5rem;
}

.title-group h1 {
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.actions {
    display: flex;
    gap: 0.75rem;
}

/* ✅ Stop Button - Red on Hover */
.actions button[severity="danger"] {
    transition: var(--transition-interactive);
}

.actions button[severity="danger"]:hover {
    background-color: var(--danger) !important;
    border-color: var(--danger) !important;
}

/* Header details */
.header-details {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
    gap: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
}

.detail-group {
    min-width: 0;
    padding: 0.9rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-background);
}

.detail-group h2 {
    margin: 0 0 0.75rem;
    color: var(--color-text-mute);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
    gap: 1rem;
}

.schedule-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.info-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
}

.info-item i {
    color: var(--color-text-mute);
    font-size: 0.875rem;
}

.info-copy {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
}

.info-copy small {
    color: var(--color-text-mute);
    font-size: 0.7rem;
}

.info-copy strong {
    overflow: hidden;
    color: var(--color-text);
    font-size: 0.82rem;
    font-weight: 500;
    text-overflow: ellipsis;
}

/* Responsive */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: 1rem;
    }

    .actions {
        width: 100%;
    }

    .actions button {
        flex: 1;
    }

    .title-group h1 {
        font-size: 1.25rem;
    }

    .header-details {
        grid-template-columns: 1fr;
    }

    .detail-grid,
    .schedule-grid {
        grid-template-columns: 1fr;
    }
}
</style>
