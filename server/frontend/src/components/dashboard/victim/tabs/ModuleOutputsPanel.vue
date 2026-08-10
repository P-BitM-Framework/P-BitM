<script setup>
import { ref, onMounted, computed } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'

const props = defineProps({
    victim: Object,
    campaign: Object
})

const toast = useToast()
const modulesData = ref([])
const loading = ref(false)
const selectedResult = ref(null)
const selectedModuleName = ref('')
const resultDetailVisible = ref(false)

const categoryIcons = {
    'Credential Access': '🔑',
    'Execution': '⚡',
    'Discovery': '🔍',
    'Collection': '📦',
    'Exfiltration': '📤',
    'Social Engineering': '🎭',
    'Browser Exploitation': '🌐',
    'Custom': '⚙️'
}

onMounted(async () => {
    await loadModulesData()
})

async function loadModulesData() {
    if (!props.campaign || !props.victim) return

    loading.value = true
    try {
        const response = await backendService.getVictimModulesData(
            props.campaign.id,
            props.victim.id
        )

        modulesData.value = response.modules || []
    } catch (error) {
        console.error('Failed to load modules data:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load module outputs',
            life: 3000
        })
    } finally {
        loading.value = false
    }
}

function showResultDetail(result, moduleName) {
    selectedResult.value = result
    selectedModuleName.value = moduleName || ''
    resultDetailVisible.value = true
}

function formatDate(dateString) {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

// Field display helpers
const sensitiveFields = ['password', 'secret', 'token', 'key', 'credit_card', 'cvv', 'iban']

function isSensitiveField(key) {
    return sensitiveFields.some(f => key.toLowerCase().includes(f))
}

function getFieldIcon(key) {
    const k = key.toLowerCase()
    if (k.includes('user') || k.includes('email')) return '👤'
    if (k.includes('password') || k.includes('secret')) return '🔑'
    if (k.includes('cookie')) return '🍪'
    if (k.includes('url')) return '🔗'
    if (k.includes('timestamp') || k.includes('time')) return '🕐'
    return '📄'
}

function getFieldSeverity(key) {
    const k = key.toLowerCase()
    if (k.includes('password') || k.includes('secret') || k.includes('token')) return 'danger'
    if (k.includes('user') || k.includes('email')) return 'success'
    if (k.includes('cookie')) return 'warn'
    return 'secondary'
}

function flattenMetadata(metadata) {
    if (!metadata || typeof metadata !== 'object') return []
    return Object.entries(metadata).map(([key, value]) => ({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
        value: typeof value === 'object' ? JSON.stringify(value) : String(value)
    }))
}

function truncateValue(value, maxLength = 60) {
    if (!value) return ''
    const str = String(value)
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str
}

function getPreviewFields(metadata) {
    if (!metadata || typeof metadata !== 'object') return []
    // Show the most relevant fields (exclude timestamp/url for preview)
    const skipInPreview = ['timestamp', 'url']
    return Object.entries(metadata)
        .filter(([k]) => !skipInPreview.includes(k.toLowerCase()))
        .slice(0, 3)
        .map(([k, v]) => ({ key: k, value: typeof v === 'object' ? JSON.stringify(v) : String(v) }))
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        toast.add({
            severity: 'success',
            summary: 'Copied',
            detail: 'JSON copied to clipboard',
            life: 2000
        })
    })
}

function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data.metadata, null, 2)], {
        type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
}

const hasData = computed(() => modulesData.value.length > 0)
</script>

<template>
    <div class="module-outputs-panel">
        <div class="panel-header">
            <h4>Module Collected Data</h4>
            <Button
                icon="pi pi-refresh"
                size="small"
                text
                rounded
                @click="loadModulesData"
                :loading="loading"
            />
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
            <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
            <p>Loading module outputs...</p>
        </div>

        <!-- Empty State -->
        <div v-else-if="!hasData" class="empty-state">
            <i class="pi pi-inbox" style="font-size: 3rem;"></i>
            <p>No module executions recorded yet</p>
            <small>Execute modules from the Scripts tab to see results here</small>
        </div>

        <!-- Modules Data -->
        <Accordion v-else :value="['0']" multiple>
            <AccordionPanel
                v-for="(module, index) in modulesData"
                :key="module.module_id"
                :value="String(index)"
            >
                <AccordionHeader>
                    <div class="module-header">
                        <div class="module-icon">
                            {{ categoryIcons[module.module_category] || '⚙️' }}
                        </div>
                        <div class="module-info">
                            <h5>{{ module.module_name }}</h5>
                            <div class="module-meta">
                                <Tag
                                    :value="module.module_category"
                                    severity="info"
                                    class="category-tag"
                                />
                                <span class="execution-count">
                                    {{ module.execution_count }} execution{{ module.execution_count > 1 ? 's' : '' }}
                                </span>
                            </div>
                        </div>
                    </div>
                </AccordionHeader>

                <AccordionContent>
                    <DataTable
                        :value="module.executions"
                        class="data-table executions-table"
                        stripedRows
                    >
                        <Column header="Time" style="width: 160px">
                            <template #body="{ data }">
                                <span class="timestamp">{{ formatDate(data.collected_at) }}</span>
                            </template>
                        </Column>

                        <Column header="Captured Data">
                            <template #body="{ data }">
                                <div class="preview-fields" v-if="data.metadata && Object.keys(data.metadata).length > 0">
                                    <div
                                        v-for="field in getPreviewFields(data.metadata)"
                                        :key="field.key"
                                        class="preview-field"
                                    >
                                        <Tag
                                            :value="field.key"
                                            :severity="getFieldSeverity(field.key)"
                                            class="field-tag"
                                        />
                                        <code class="field-value">{{ isSensitiveField(field.key) ? '••••••••' : truncateValue(field.value, 30) }}</code>
                                    </div>
                                </div>
                                <span v-else class="no-data">No data</span>
                            </template>
                        </Column>

                        <Column header="Actions" style="width: 120px">
                            <template #body="{ data }">
                                <div class="action-buttons">
                                    <Button
                                        icon="pi pi-eye"
                                        size="small"
                                        text
                                        rounded
                                        @click="showResultDetail(data, module.module_name)"
                                        v-tooltip.top="'View Details'"
                                    />
                                    <Button
                                        icon="pi pi-download"
                                        size="small"
                                        text
                                        rounded
                                        @click="downloadJSON(data, `${module.module_name}-${data.id}.json`)"
                                        v-tooltip.top="'Download JSON'"
                                    />
                                </div>
                            </template>
                        </Column>
                    </DataTable>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>

        <!-- Result Detail Dialog -->
        <Dialog
            v-model:visible="resultDetailVisible"
            :header="selectedResult ? `${selectedModuleName} — ${formatDate(selectedResult.collected_at)}` : 'Collected Data'"
            :style="{ width: '70vw', maxHeight: '80vh' }"
            modal
            :draggable="false"
        >
            <div v-if="selectedResult" class="result-detail">
                <!-- Fields Table -->
                <div class="fields-view">
                    <h6>Collected Data</h6>
                    <DataTable
                        :value="flattenMetadata(selectedResult.metadata)"
                        stripedRows
                        class="data-table fields-table"
                    >
                        <Column header="Field" style="width: 200px">
                            <template #body="{ data }">
                                <div class="field-cell">
                                    <span class="field-icon">{{ getFieldIcon(data.key) }}</span>
                                    <Tag
                                        :value="data.label"
                                        :severity="getFieldSeverity(data.key)"
                                    />
                                </div>
                            </template>
                        </Column>
                        <Column header="Value">
                            <template #body="{ data }">
                                <div class="value-cell">
                                    <code class="value-code">{{ data.value }}</code>
                                    <Button
                                        icon="pi pi-copy"
                                        text
                                        rounded
                                        size="small"
                                        @click="copyToClipboard(data.value)"
                                        v-tooltip.left="'Copy'"
                                    />
                                </div>
                            </template>
                        </Column>
                    </DataTable>
                </div>

                <!-- Collapsible JSON View -->
                <details class="json-details">
                    <summary>Raw JSON</summary>
                    <div class="json-view">
                        <div class="json-header">
                            <Button
                                icon="pi pi-copy"
                                label="Copy JSON"
                                size="small"
                                text
                                @click="copyToClipboard(JSON.stringify(selectedResult.metadata, null, 2))"
                            />
                        </div>
                        <pre class="json-content">{{ JSON.stringify(selectedResult.metadata, null, 2) }}</pre>
                    </div>
                </details>
            </div>

            <template #footer>
                <Button
                    label="Close"
                    icon="pi pi-times"
                    @click="resultDetailVisible = false"
                />
                <Button
                    label="Download JSON"
                    icon="pi pi-download"
                    severity="secondary"
                    @click="downloadJSON(selectedResult, `module-output-${selectedResult.id}.json`)"
                />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.module-outputs-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 1rem;
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

/* Loading & Empty States */
.loading-state,
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    text-align: center;
    color: var(--color-text-mute);
}

.empty-state i {
    color: var(--color-text-mute);
    margin-bottom: 1rem;
}

.empty-state p {
    margin: 0.5rem 0;
    font-size: 1rem;
}

.empty-state small {
    color: var(--color-text-mute);
    font-size: 0.875rem;
}

/* Accordion Header */
.module-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
}

.module-icon {
    font-size: 2rem;
    flex-shrink: 0;
}

.module-info {
    flex: 1;
    min-width: 0;
}

.module-info h5 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0 0 0.25rem 0;
}

.module-meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.category-tag {
    font-size: 0.7rem;
}

.execution-count {
    font-size: 0.8rem;
    color: var(--color-text-mute);
}

/* Executions Table */
.executions-table {
    margin-top: 0.5rem;
}

.timestamp {
    font-size: 0.85rem;
    color: var(--color-text);
}

/* Preview fields in table */
.preview-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.preview-field {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.field-tag {
    font-size: 0.7rem;
}

.field-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--color-text);
    background: var(--color-background-mute);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
}

.no-data {
    color: var(--color-text-mute);
    font-style: italic;
    font-size: 0.85rem;
}

.action-buttons {
    display: flex;
    gap: 0.25rem;
}

/* Result Detail Dialog */
.result-detail {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.fields-view h6 {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0 0 0.75rem 0;
}

.fields-table {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

.field-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.field-icon {
    font-size: 1rem;
}

.value-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: space-between;
}

.value-code {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-text);
    background: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    word-break: break-all;
}

/* Collapsible JSON */
.json-details {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

.json-details summary {
    cursor: pointer;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-mute);
    background: var(--color-background-mute);
    user-select: none;
}

.json-details summary:hover {
    color: var(--color-heading);
}

.json-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}

.json-content {
    background: var(--code-canvas);
    border: 1px solid var(--code-border);
    border-radius: 6px;
    padding: 1rem;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    line-height: 1.5;
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
    color: var(--code-text);
}

/* Responsive */
@media (max-width: 768px) {
    .module-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .action-buttons {
        flex-direction: column;
    }
}
</style>
