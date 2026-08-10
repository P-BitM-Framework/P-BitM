<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'

const props = defineProps({
    victim: {
        type: Object,
        required: true
    },
    campaign: {
        type: Object,
        required: true
    }
})

const ConsolePanel = defineAsyncComponent(() => import('./tabs/ConsolePanel.vue'))
const ModulesPanel = defineAsyncComponent(() => import('./tabs/ModulesPanel.vue'))
const ModuleOutputsPanel = defineAsyncComponent(() => import('./tabs/ModuleOutputsPanel.vue'))
const DataPanel = defineAsyncComponent(() => import('./tabs/DataPanel.vue'))
const TimelinePanel = defineAsyncComponent(() => import('./tabs/TimelinePanel.vue'))
const CookiesPanel = defineAsyncComponent(() => import('./tabs/CookiesPanel.vue'))
const VictimFileCard = defineAsyncComponent(() => import('@/components/dashboard/VictimFileCard.vue'))
const SendFileCard = defineAsyncComponent(() => import('@/components/dashboard/SendFileCard.vue'))

const areas = computed(() => [
    {
        key: 'monitor',
        label: 'Monitor',
        icon: 'pi pi-desktop',
        tools: [
            { key: 'console', label: 'Console', icon: 'pi pi-code', component: ConsolePanel }
        ]
    },
    {
        key: 'actions',
        label: 'Actions',
        icon: 'pi pi-bolt',
        tools: [
            { key: 'modules', label: 'Modules', icon: 'pi pi-bolt', component: ModulesPanel, campaign: true },
            ...(props.victim.is_active
                ? [{ key: 'upload', label: 'Upload File', icon: 'pi pi-upload', component: SendFileCard, campaign: true }]
                : [])
        ]
    },
    {
        key: 'data',
        label: 'Collected Data',
        icon: 'pi pi-database',
        tools: [
            { key: 'data', label: 'Overview', icon: 'pi pi-database', component: DataPanel, polling: true },
            { key: 'outputs', label: 'Module Results', icon: 'pi pi-list', component: ModuleOutputsPanel, campaign: true },
            { key: 'files', label: 'Files', icon: 'pi pi-file', component: VictimFileCard, campaign: true }
        ]
    },
    {
        key: 'cookies',
        label: 'Cookies',
        icon: 'pi pi-box',
        tools: [
            { key: 'cookies', label: 'Cookies', icon: 'pi pi-box', component: CookiesPanel, polling: true }
        ]
    },
    {
        key: 'activity',
        label: 'Activity',
        icon: 'pi pi-chart-line',
        tools: [
            { key: 'timeline', label: 'Timeline', icon: 'pi pi-chart-line', component: TimelinePanel, polling: true }
        ]
    }
])

const activeArea = ref('monitor')
const selectedTools = ref({
    monitor: 'console',
    data: 'data',
    cookies: 'cookies',
    actions: 'modules',
    activity: 'timeline'
})

const currentArea = computed(() => areas.value.find((area) => area.key === activeArea.value) || areas.value[0])
const currentTool = computed(() => {
    const selected = selectedTools.value[activeArea.value]
    return currentArea.value.tools.find((tool) => tool.key === selected) || currentArea.value.tools[0]
})

const currentPanelProps = computed(() => {
    const panelProps = { victim: props.victim }
    if (currentTool.value.campaign) panelProps.campaign = props.campaign
    if (currentTool.value.polling) panelProps.active = true
    return panelProps
})

function selectArea(area) {
    activeArea.value = area.key
}

function selectTool(tool) {
    selectedTools.value[activeArea.value] = tool.key
}

watch(
    () => props.victim.is_active,
    (isActive) => {
        if (!isActive && selectedTools.value.actions === 'upload') {
            selectedTools.value.actions = 'modules'
        }
    }
)
</script>

<template>
    <section class="tool-workspace">
        <nav class="tool-area-nav" aria-label="Session tools">
            <button
                v-for="area in areas"
                :key="area.key"
                type="button"
                :class="{ active: activeArea === area.key }"
                @click="selectArea(area)"
            >
                <i :class="area.icon"></i>
                <span>{{ area.label }}</span>
            </button>
        </nav>

        <div class="tool-content">
            <header class="tool-content-header">
                <div>
                    <h3>{{ currentArea.label }}</h3>
                    <p v-if="activeArea === 'monitor'">Run commands against the active browser session.</p>
                    <p v-else-if="activeArea === 'data'">Inspect information and files collected during the session.</p>
                    <p v-else-if="activeArea === 'cookies'">Review cookies captured from the browser session.</p>
                    <p v-else-if="activeArea === 'actions'">Run approved modules or transfer files to the session.</p>
                    <p v-else>Review the chronological event stream.</p>
                </div>

                <div v-if="currentArea.tools.length > 1" class="tool-switcher">
                    <button
                        v-for="tool in currentArea.tools"
                        :key="tool.key"
                        type="button"
                        :class="{ active: currentTool.key === tool.key }"
                        @click="selectTool(tool)"
                    >
                        <i :class="tool.icon"></i>
                        {{ tool.label }}
                    </button>
                </div>
            </header>

            <div class="panel-container">
                <Transition name="fade" mode="out-in">
                    <Suspense>
                        <KeepAlive>
                            <component
                                :is="currentTool.component"
                                :key="currentTool.key"
                                v-bind="currentPanelProps"
                            />
                        </KeepAlive>
                        <template #fallback>
                            <Skeleton height="180px" borderRadius="8px" />
                        </template>
                    </Suspense>
                </Transition>
            </div>
        </div>
    </section>
</template>

<style scoped>
.tool-workspace {
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: 10px;
    background: var(--color-background-soft);
}

.tool-area-nav {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    border-bottom: 1px solid var(--color-border);
    background: var(--color-background-mute);
}

.tool-area-nav button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.55rem;
    min-height: 52px;
    border: 0;
    border-right: 0;
    background: transparent;
    color: var(--color-text-mute);
    font: inherit;
    font-weight: 500;
    cursor: pointer;
}

.tool-area-nav button:last-child {
    border-right: 0;
}

.tool-area-nav button:hover {
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
    color: var(--color-heading);
}

.tool-area-nav button.active {
    box-shadow: inset 0 -2px 0 var(--color-accent);
    background: var(--color-background-soft);
    color: var(--color-accent);
}

.tool-content {
    padding: 1.25rem;
}

.tool-content-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 1.25rem;
}

.tool-content-header h3,
.tool-content-header p {
    margin: 0;
}

.tool-content-header h3 {
    color: var(--color-heading);
    font-size: 1.05rem;
    font-weight: 600;
}

.tool-content-header p {
    margin-top: 0.25rem;
    color: var(--color-text-mute);
    font-size: 0.82rem;
}

.tool-switcher {
    display: flex;
    padding: 0.25rem;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-background-mute);
}

.tool-switcher button {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.45rem 0.7rem;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--color-text-mute);
    font: inherit;
    font-size: 0.78rem;
    cursor: pointer;
}

.tool-switcher button.active {
    background: var(--color-background-soft);
    color: var(--color-heading);
    box-shadow: var(--shadow-sm);
}

.panel-container {
    min-height: 180px;
}
</style>
