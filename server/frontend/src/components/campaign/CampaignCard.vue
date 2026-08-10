<script setup>
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import { formatDateLocal, getCampaignStatusConfig } from '@/utils/utils.js'

const props = defineProps({
    campaign: {
        type: Object,
        required: true
    }
})

const emit = defineEmits(['select', 'contextmenu', 'copy'])

const handleContextMenu = (event) => {
    emit('contextmenu', event, props.campaign)
}

const handleClick = () => {
    emit('select', props.campaign)
}

// Computed
const statusConfig = computed(() => getCampaignStatusConfig(props.campaign.status))

const progressPercentage = computed(() => {
    if (!props.campaign.total_targets) return 0
    return Math.round((props.campaign.emails_sent / props.campaign.total_targets) * 100)
})

const openRate = computed(() => {
    if (!props.campaign.total_targets) return 0
    return Math.round((props.campaign.emails_opened / props.campaign.total_targets) * 100)
})

const clickRate = computed(() => {
    if (!props.campaign.total_targets) return 0
    return Math.round((props.campaign.links_clicked / props.campaign.total_targets) * 100)
})

const dataSubmittedRate = computed(() => {
    if (!props.campaign.total_targets) return 0
    return Math.round((props.campaign.data_submitted / props.campaign.total_targets) * 100)
})

const isStandalone = computed(() => props.campaign.campaign_type === 'standalone')

const scheduledStart = computed(() => props.campaign.scheduled_start
    ? formatDateLocal(props.campaign.scheduled_start)
    : 'Not scheduled')
const scheduledEnd = computed(() => props.campaign.scheduled_end
    ? formatDateLocal(props.campaign.scheduled_end)
    : 'Not scheduled')
</script>

<template>
    <Card
        class="campaign-card"
        @click="handleClick"
        @contextmenu="handleContextMenu"
    >
        <template #content>
            <!-- Header -->
            <div class="card-header">
                <h3>{{ campaign.name }}</h3>
                <div class="card-header-tags">
                    <Tag
                        v-if="isStandalone"
                        value="Standalone"
                        severity="info"
                        icon="pi pi-link"
                    />
                    <Tag
                        :value="statusConfig.label"
                        :severity="statusConfig.severity"
                        :icon="statusConfig.icon"
                    />
                </div>
            </div>

            <!-- Progress Bar -->
            <div v-if="!isStandalone" class="progress-section">
                <div class="progress-label">
                    <span>{{ campaign.emails_sent }}/{{ campaign.total_targets }} sent</span>
                    <span>{{ progressPercentage }}%</span>
                </div>
                <ProgressBar :value="progressPercentage" :showValue="false" />
            </div>

            <!-- Quick Stats -->
            <div v-if="!isStandalone" class="quick-stats">
                <!-- <div class="stat">
                    <span class="stat-value">{{ campaign.victims_count || 0 }}</span>
                    <span class="stat-label">Victims</span>
                    <span v-if="activeVictims > 0" class="stat-badge">
                        {{ activeVictims }} active
                    </span>
                </div> -->
                <div class="stat">
                    <span class="stat-value">{{ openRate }}%</span>
                    <span class="stat-label">Opened</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{{ clickRate }}%</span>
                    <span class="stat-label">Clicked</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{{ dataSubmittedRate }}%</span>
                    <span class="stat-label">Submitted</span>
                </div>
            </div>

            <div v-else class="quick-stats standalone-stats">
                <div class="stat">
                    <span class="stat-value">{{ campaign.total_targets || 0 }}</span>
                    <span class="stat-label">Links</span>
                </div>
                <div class="stat">
                    <span class="stat-value success">{{ campaign.data_collected || 0 }}</span>
                    <span class="stat-label">Captured</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{{ campaign.total_screenshots || 0 }}</span>
                    <span class="stat-label">Screenshots</span>
                </div>
            </div>
        </template>

        <template #footer>
            <div class="card-footer">
                <div class="campaign-schedule" v-if="!isStandalone">
                    <div class="schedule-item">
                        <i class="pi pi-play-circle"></i>
                        <span class="schedule-copy">
                            <small>Email sending starts</small>
                            <strong>{{ scheduledStart }}</strong>
                        </span>
                    </div>
                    <div class="schedule-item">
                        <i class="pi pi-stop-circle"></i>
                        <span class="schedule-copy">
                            <small>Email sending ends</small>
                            <strong>{{ scheduledEnd }}</strong>
                        </span>
                    </div>
                </div>
                <div class="campaign-date-range" v-else-if="isStandalone">
                    <i class="pi pi-link"></i>
                    <span>Tracking-link campaign</span>
                </div>

                <Button
                    label="Open"
                    icon="pi pi-arrow-right"
                    iconPos="right"
                    text
                    size="small"
                    @click="emit('select', campaign)"
                />
            </div>
        </template>
    </Card>
</template>

<style scoped>
.campaign-card {
    cursor: pointer;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    transform: translate3d(0, 0, 0);
    transition:
        border-color 180ms var(--ease-standard),
        transform 220ms cubic-bezier(0.16, 1, 0.3, 1);
    will-change: transform;
}

.campaign-card:hover {
    border-color: var(--color-border-hover);
    transform: translate3d(0, -2px, 0);
}

/* Remove default padding */
.campaign-card :deep(.p-card-body) {
    padding: 1rem;
}

.campaign-card :deep(.p-card-content) {
    padding: 0;
}

.campaign-card :deep(.p-card-footer) {
    padding: 0.75rem 0 0 0;
    border-top: 1px solid var(--color-border);
}

/* Header */
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.card-header h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.card-header-tags {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.4rem;
    flex-shrink: 0;
}

/* Quick Stats */
.quick-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.stat {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.stat-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-heading);
    line-height: 1;
}

.stat-value.success {
    color: var(--color-success);
}

.standalone-stats {
    margin-top: 1.75rem;
}

.stat-label {
    font-size: 0.7rem;
    color: var(--color-text-mute);
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.stat-badge {
    font-size: 0.65rem;
    padding: 0.125rem 0.375rem;
    border-radius: 8px;
    background-color: var(--success-subtle);
    color: var(--success);
    width: fit-content;
    margin-top: 0.25rem;
}

/* Progress */
.progress-section {
    margin-bottom: 1rem;
}

.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--color-text-mute);
    margin-bottom: 0.375rem;
}

.progress-label span:last-child {
    font-weight: 600;
    color: var(--color-text);
}

.progress-section :deep(.p-progressbar) {
    height: 4px;
}

/* Footer */
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

/* Campaign Date Range */
.campaign-schedule {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    flex: 1;
    min-width: 0;
}

.schedule-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
}

.schedule-item i {
    color: var(--color-text-mute);
    font-size: 0.8rem;
    flex-shrink: 0;
}

.schedule-copy {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
}

.schedule-copy small {
    color: var(--color-text-mute);
    font-size: 0.65rem;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

.schedule-copy strong {
    color: var(--color-text);
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* @media (max-width: 768px) {
    .card-footer {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
    }

    .campaign-date-range {
        order: 1;
    }
} */

@media (max-width: 480px) {
    .campaign-schedule {
        grid-template-columns: 1fr;
    }
}
</style>

<style>
/* Context Menu Styles (Global) */
.delete-menu-item .p-contextmenu-item-link {
    color: var(--danger) !important;
    font-weight: 600;
}

.delete-menu-item .p-contextmenu-item-icon {
    color: var(--danger) !important;
}

.delete-menu-item .p-contextmenu-item-link:hover,
.delete-menu-item .p-contextmenu-item-link:focus {
    background: var(--danger-subtle) !important;
}
</style>
