<script setup>
import { computed } from 'vue'
import SentIcon from 'virtual:icons/material-symbols/send-rounded'
import OpenedIcon from 'virtual:icons/material-symbols/mark-email-read-rounded'
import ClickedIcon from 'virtual:icons/material-symbols/ads-click'
import DataIcon from 'virtual:icons/material-symbols/interactive-space'

const props = defineProps({
    campaign: Object
})

const funnelStages = computed(() => {
    const total = props.campaign.total_targets || 1

    return [
        {
            id: 'sent',
            icon: SentIcon,
            label: 'Sent',
            count: props.campaign.emails_sent || 0,
            total: total,
            percentage: Math.round(((props.campaign.emails_sent || 0) / total) * 100)
        },
        {
            id: 'opened',
            icon: OpenedIcon,
            label: 'Opened',
            count: props.campaign.emails_opened || 0,
            total: total,
            percentage: Math.round(((props.campaign.emails_opened || 0) / total) * 100)
        },
        {
            id: 'clicked',
            icon: ClickedIcon,
            label: 'Clicked',
            count: props.campaign.links_clicked || 0,
            total: total,
            percentage: Math.round(((props.campaign.links_clicked || 0) / total) * 100)
        },
        {
            id: 'collected',
            icon: DataIcon,
            label: 'Data Captured',
            count: props.campaign.data_collected || 0,
            total: total,
            percentage: Math.round(((props.campaign.data_collected || 0) / total) * 100)
        }
    ]
})

function getColorForPercentage(percentage, stage) {
    if (stage === 'sent') return 'var(--info)'
    if (stage === 'opened') {
        if (percentage >= 70) return 'var(--success)'
        if (percentage >= 40) return 'var(--warning)'
        return 'var(--danger)'
    }
    if (stage === 'clicked') {
        if (percentage >= 50) return 'var(--warning)'
        if (percentage >= 30) return 'var(--warning)'
        return 'var(--text-muted)'
    }
    if (stage === 'collected') {
        if (percentage >= 20) return 'var(--danger)'
        if (percentage >= 10) return 'var(--warning)'
        return 'var(--text-muted)'
    }
    return 'var(--text-muted)'
}
</script>

<template>
    <div class="campaign-funnel">
        <h2 class="section-title">
            <i class="pi pi-chart-bar"></i>
            Campaign Summary
        </h2>

        <div class="funnel-grid">
            <div
                v-for="stage in funnelStages"
                :key="stage.id"
                class="funnel-card"
            >
                <component :is="stage.icon" class="card-icon" role="img" :aria-label="stage.label" />
                <div class="card-label">{{ stage.label }}</div>

                <!-- Progress Ring -->
                <div class="progress-ring-container">
                    <svg class="progress-ring" width="100" height="100">
                        <circle
                            cx="50"
                            cy="50"
                            r="42"
                            fill="transparent"
                            stroke="var(--color-border)"
                            stroke-width="8"
                        />
                        <circle
                            cx="50"
                            cy="50"
                            r="42"
                            fill="transparent"
                            :stroke="getColorForPercentage(stage.percentage, stage.id)"
                            stroke-width="8"
                            :stroke-dasharray="264"
                            :stroke-dashoffset="264 - (264 * stage.percentage / 100)"
                            stroke-linecap="round"
                            transform="rotate(-90 50 50)"
                            class="progress-circle"
                        />
                    </svg>
                    <div class="progress-text">
                        <span class="percentage">{{ stage.percentage }}%</span>
                    </div>
                </div>

                <div class="card-count">{{ stage.count }} / {{ stage.total }}</div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.campaign-funnel {
    background-color: var(--color-background-soft);
    /* border: 1px solid var(--color-border); */
    border-radius: 8px;
    padding: 1.5rem;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0 0 1.5rem 0;
}

.section-title i {
    color: var(--color-text-mute);
}

.funnel-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1.5rem;
}

.funnel-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}

.card-icon {
    width: 2rem;
    height: 2rem;
    font-size: 2rem;
    color: var(--color-text-mute);
    margin-bottom: 0.5rem;
}

.card-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-mute);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 1rem;
}

.progress-ring-container {
    position: relative;
    margin-bottom: 0.75rem;
}

.progress-circle {
    transition: stroke-dashoffset 0.6s ease;
}

.progress-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}

.percentage {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-heading);
}

.card-count {
    font-size: 0.875rem;
    color: var(--color-text-mute);
    font-weight: 500;
}

/* Responsive */
@media (max-width: 768px) {
    .funnel-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
