<script setup>
import { computed } from 'vue'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import { formatDateLocal, getCampaignStatusConfig } from '@/utils/utils.js'

const props = defineProps({
    campaign: {
        type: Object,
        required: true
    }
})

const emit = defineEmits(['select', 'contextmenu'])

const statusConfig = computed(() => getCampaignStatusConfig(props.campaign.status))

const isStandalone = computed(() => props.campaign.campaign_type === 'standalone')

const campaignStats = computed(() => {
    const total = props.campaign.total_targets || 0
    const sent = props.campaign.emails_sent || 0
    const opened = props.campaign.emails_opened || 0
    const clicked = props.campaign.links_clicked || 0
    const submitted = props.campaign.data_submitted || 0
    const collected = props.campaign.data_collected || 0
    const screenshots = props.campaign.total_screenshots || 0

    return { total, sent, opened, clicked, submitted, collected, screenshots }
})

const scheduledStart = computed(() => props.campaign.scheduled_start
    ? formatDateLocal(props.campaign.scheduled_start)
    : 'Not scheduled')
const scheduledEnd = computed(() => props.campaign.scheduled_end
    ? formatDateLocal(props.campaign.scheduled_end)
    : 'Not scheduled')

function handleClick() {
    emit('select', props.campaign)
}

function handleContextMenu(event) {
    emit('contextmenu', event, props.campaign)
}
</script>

<template>
    <div
        class="campaign-list-item"
        @click="handleClick"
        @contextmenu="handleContextMenu"
    >
        <!-- Left: Status + Info -->
        <div class="item-main">
            <div class="item-status">
                <i :class="[statusConfig.icon, `status-${campaign.status}`]"></i>
            </div>

            <div class="item-info">
                <h3 class="item-title">{{ campaign.name }}</h3>
                <p v-if="isStandalone" class="item-meta">
                    <i class="pi pi-link"></i>
                    <span>Standalone access</span>
                    <span class="meta-separator">•</span>
                    <span>{{ campaignStats.total }} targets</span>
                </p>
                <div v-else class="item-schedule">
                    <span><small>Sending starts</small>{{ scheduledStart }}</span>
                    <span><small>Sending ends</small>{{ scheduledEnd }}</span>
                    <span class="target-count">{{ campaignStats.total }} targets</span>
                </div>
            </div>
        </div>

        <!-- Center: Stats -->
        <div class="item-stats" :class="{ 'item-stats--standalone': isStandalone }">
            <template v-if="isStandalone">
                <div class="stat-item">
                    <span class="stat-label">Links</span>
                    <span class="stat-value">{{ campaignStats.total }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Captured</span>
                    <span class="stat-value success">{{ campaignStats.collected }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Screenshots</span>
                    <span class="stat-value">{{ campaignStats.screenshots }}</span>
                </div>
            </template>
            <template v-else>
                <div class="stat-item">
                    <span class="stat-label">Sent</span>
                    <span class="stat-value">{{ campaignStats.sent }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Opened</span>
                    <span class="stat-value">{{ campaignStats.opened }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Clicked</span>
                    <span class="stat-value">{{ campaignStats.clicked }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Submitted</span>
                    <span class="stat-value success">{{ campaignStats.submitted }}</span>
                </div>
            </template>
        </div>

        <!-- Right: Actions -->
        <div class="item-actions">
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
            <Button
                icon="pi pi-chevron-right"
                text
                rounded
                class="action-btn"
                @click.stop="handleClick"
            />
        </div>
    </div>
</template>

<style scoped>
.campaign-list-item {
    display: flex;
    align-items: center;
    gap: 2rem;
    padding: 1.25rem;
    background: var(--color-background-soft);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: var(--transition-interactive);
}

.campaign-list-item:hover {
    background: var(--color-background-mute);
    border-color: var(--color-border-hover);
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
}

/* Left Section */
.item-main {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex: 1;
    min-width: 0;
}

.item-status i {
    font-size: 1rem;
    flex-shrink: 0;
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

.item-info {
    flex: 1;
    min-width: 0;
}

.item-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0 0 0.25rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.item-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--color-text-mute);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.item-meta i {
    font-size: 0.75rem;
    flex-shrink: 0;
}

.meta-separator {
    color: var(--color-border);
}

.item-schedule {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-width: 0;
    color: var(--color-text);
    font-size: 0.78rem;
}

.item-schedule > span:not(.target-count) {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
}

.item-schedule small {
    color: var(--color-text-mute);
    font-size: 0.65rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.target-count {
    align-self: flex-end;
    color: var(--color-text-mute);
    white-space: nowrap;
}

/* Center Section - Stats */
.item-stats {
    display: flex;
    gap: 2rem;
    padding: 0 1rem;
    flex-shrink: 0;
}

.item-stats--standalone {
    min-width: 270px;
    justify-content: flex-end;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    min-width: 50px;
}

.stat-label {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}

.stat-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-heading);
}

.stat-value.success {
    color: var(--success);
}

/* Right Section - Actions */
.item-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
}

.action-btn {
    opacity: 0.6;
    transition: opacity 0.2s;
}

.campaign-list-item:hover .action-btn {
    opacity: 1;
}

/* Tablet: hide the stats, stack everything below */
@media (max-width: 1280px) {
    .campaign-list-item {
        gap: 1.5rem;
    }

    .item-stats {
        gap: 1.5rem;
        padding: 0 0.5rem;
    }
}

@media (max-width: 1024px) {
    .campaign-list-item {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
    }

    .item-main {
        width: 100%;
    }

    .item-stats {
        justify-content: space-around;
        padding: 0;
        gap: 1rem;
        border-top: 1px solid var(--color-border);
        padding-top: 1rem;
    }

    .item-actions {
        justify-content: space-between;
        border-top: 1px solid var(--color-border);
        padding-top: 1rem;
    }

    .stat-item {
        min-width: auto;
    }
}

@media (max-width: 640px) {
    .item-schedule {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .target-count {
        grid-column: 1 / -1;
    }
}

/* Mobile: Compatto */
@media (max-width: 640px) {
    .campaign-list-item {
        padding: 1rem;
        gap: 0.75rem;
    }

    .item-title {
        font-size: 0.95rem;
    }

    .item-meta {
        font-size: 0.75rem;
    }

    .item-stats {
        gap: 0.75rem;
        padding: 0;
        padding-top: 0.75rem;
        border-top: 1px solid var(--color-border);
    }

    .stat-item {
        gap: 0.125rem;
    }

    .stat-label {
        font-size: 0.65rem;
    }

    .stat-value {
        font-size: 1rem;
    }

    .item-actions {
        gap: 0.5rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--color-border);
    }

    .action-btn {
        padding: 0.25rem;
    }
}

/* Extra Small: Molto compatto */
@media (max-width: 480px) {
    .campaign-list-item {
        padding: 0.75rem;
        border-radius: 6px;
    }

    .item-status i {
        font-size: 0.9rem;
    }

    .item-title {
        font-size: 0.9rem;
    }

    .item-meta {
        display: none;
    }

    .item-stats {
        gap: 0.5rem;
    }

    .stat-item {
        min-width: 40px;
    }

    .stat-label {
        font-size: 0.6rem;
    }

    .stat-value {
        font-size: 0.9rem;
    }
}
</style>
