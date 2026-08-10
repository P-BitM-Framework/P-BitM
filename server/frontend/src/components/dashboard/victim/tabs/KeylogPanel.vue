<script setup>
import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'

const props = defineProps({
    keylogs: {
        type: String,
        default: ""
    },
    isLive: {
        type: Boolean,
        default: false
    },
    truncated: {
        type: Boolean,
        default: false
    },
    originalSize: {
        type: Number,
        default: 0
    }
})

const toast = useToast()

const keylogs = ref(props.keylogs || "")
const searchQuery = ref('')

const markerPattern = /^\[(SESSION STARTED|TIMESTAMP|KEYLOG ROTATED)\b.*\]$/

function trimEmptyEdges(lines) {
    let start = 0
    let end = lines.length
    while (start < end && !lines[start].trim()) start += 1
    while (end > start && !lines[end - 1].trim()) end -= 1
    return lines.slice(start, end)
}

const keylogSections = computed(() => {
    if (!keylogs.value) return []

    const sections = []
    let marker = ''
    let contentLines = []

    const appendSection = () => {
        const content = trimEmptyEdges(contentLines).join('\n')
        if (marker || content) {
            sections.push({ marker, content })
        }
    }

    for (const line of keylogs.value.split('\n')) {
        if (markerPattern.test(line)) {
            appendSection()
            marker = line
            contentLines = []
        } else {
            contentLines.push(line)
        }
    }
    appendSection()
    return sections
})

const filteredSections = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()
    const sections = query
        ? keylogSections.value.filter(section =>
            section.marker.toLowerCase().includes(query)
            || section.content.toLowerCase().includes(query)
        )
        : keylogSections.value
    return sections.slice(-50)
})

const formattedOriginalSize = computed(() => {
    if (props.originalSize < 1024) return `${props.originalSize} B`
    if (props.originalSize < 1024 * 1024) {
        return `${(props.originalSize / 1024).toFixed(1)} KB`
    }
    return `${(props.originalSize / (1024 * 1024)).toFixed(1)} MB`
})

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
    toast.add({
        severity: 'success',
        summary: 'Copied',
        detail: 'Text copied to clipboard',
        life: 2000
    })
}

function exportKeylogs() {
    if (!keylogs.value) return

    const blob = new Blob([keylogs.value], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `keylog_${Date.now()}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast.add({
        severity: 'success',
        summary: 'Export',
        detail: 'Keylog downloaded',
        life: 2000
    })
}

watch(() => props.keylogs, (newKeylogs) => {
    keylogs.value = typeof newKeylogs === 'string' ? newKeylogs : ''
})
</script>

<template>
    <Card class="keylog-panel">
        <template #title>
            <div class="panel-header">
                <h3>
                    <i class="pi pi-keyboard"></i>
                    Live Keylog
                    <span
                        class="recording-indicator"
                        :class="{ stopped: !isLive }"
                    >
                        <i class="pi pi-circle-fill"></i>
                        {{ isLive ? 'Recording' : 'Stopped' }}
                    </span>
                </h3>
            </div>
        </template>

        <template #content>
            <!-- Controls -->
            <div class="keylog-controls">
                <div class="controls-left">
                    <Button
                        icon="pi pi-download"
                        label="Export"
                        size="small"
                        outlined
                        :disabled="!keylogs"
                        @click="exportKeylogs"
                    />
                </div>

                <div class="controls-right">
                    <IconField iconPosition="left">
                        <InputIcon>
                            <i class="pi pi-search" />
                        </InputIcon>
                        <InputText
                            v-model="searchQuery"
                            placeholder="Search keylog..."
                        />
                    </IconField>
                </div>
            </div>

            <div v-if="truncated" class="truncation-notice">
                Showing the most recent keylog data (original size:
                {{ formattedOriginalSize }}).
            </div>

            <!-- Keylog Feed -->
            <div class="keylog-feed">
                <div class="keylog-entry">
                    <div
                        v-for="(section, index) in filteredSections"
                        :key="index"
                        class="keylog-section"
                    >
                        <div v-if="section.marker" class="entry-marker">
                            {{ section.marker }}
                        </div>
                        <div v-if="section.content" class="entry-main">
                            <div class="entry-content">{{ section.content }}</div>
                            <Button
                                icon="pi pi-copy"
                                text
                                rounded
                                size="small"
                                @click="copyToClipboard(section.content)"
                                class="copy-btn"
                            />
                        </div>
                    </div>
                </div>

                <!-- Empty State -->
                <div v-if="filteredSections.length === 0" class="empty-state">
                    <i class="pi pi-inbox"></i>
                    <p>No keystrokes captured yet</p>
                </div>
            </div>
        </template>
    </Card>
</template>

<style scoped>
.keylog-panel {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.keylog-panel :deep(.p-card-body) {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.keylog-panel :deep(.p-card-content) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 0;
}

.panel-header h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.recording-indicator {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.75rem;
    color: var(--success);
    font-weight: 500;
}

.recording-indicator i {
    font-size: 0.5rem;
    animation: pulse 2s infinite;
}

.recording-indicator.stopped {
    color: var(--color-text-mute);
}

.recording-indicator.stopped i {
    animation: none;
}

.truncation-notice {
    margin: 0.75rem 0;
    padding: 0.625rem 0.75rem;
    border: 1px solid color-mix(in srgb, var(--warning) 35%, transparent);
    border-radius: 6px;
    color: var(--warning);
    font-size: 0.8125rem;
}

.entry-marker {
    color: var(--color-text-mute);
    font-style: italic;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    padding: 0.25rem 0.125rem;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.keylog-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--color-border);
    gap: 1rem;
}

.controls-left,
.controls-right {
    display: flex;
    gap: 0.5rem;
}

.search-input {
    width: auto;
}

.keylog-feed {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: auto;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: 0.75rem;
}

.keylog-entry {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.keylog-section {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.entry-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.625rem 0.75rem;
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    transition: var(--transition-interactive);
}

.entry-main:hover {
    border-color: var(--color-border-hover);
    box-shadow: var(--shadow-xs);
}

.entry-content {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    color: var(--color-text);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.copy-btn {
    opacity: 0;
    transition: opacity 0.2s;
    flex-shrink: 0;
    margin-left: 0.5rem;
}

.entry-main:hover .copy-btn {
    opacity: 1;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--color-text-mute);
}

.empty-state i {
    font-size: 2.5rem;
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
    font-size: 0.875rem;
}

/* Scrollbar Styling */
.keylog-feed::-webkit-scrollbar {
    width: 8px;
}

.keylog-feed::-webkit-scrollbar-track {
    background: var(--color-background);
    border-radius: 4px;
}

.keylog-feed::-webkit-scrollbar-thumb {
    background: var(--color-border-hover);
    border-radius: 4px;
}

.keylog-feed::-webkit-scrollbar-thumb:hover {
    background: var(--color-text-mute);
}
</style>
