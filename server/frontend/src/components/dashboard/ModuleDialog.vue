<template>
  <Dialog
    v-model:visible="visible"
    :header="mode === 'edit' ? 'Edit Module' : 'New Module'"
    class="app-text-editor-dialog module-editor-dialog"
    :style="{ width: '95vw', maxWidth: '1800px' }"
    modal
    :draggable="false"
    :closable="!loading"
  >
    <template #header>
      <div class="dialog-header-custom">
        <span class="dialog-title">{{ mode === 'edit' ? 'Edit Module' : 'New Module' }}</span>
        <input
          ref="jsonFileInput"
          type="file"
          accept="application/json,.json"
          style="display: none"
          @change="handleJsonImport"
        />
        <Button
          label="Import JSON"
          icon="pi pi-upload"
          severity="secondary"
          outlined
          size="small"
          @click="$refs.jsonFileInput.click()"
        />
      </div>
    </template>
    <div class="dialog-layout">
      <!-- Left: Fields -->
      <div class="settings-sidebar">
        <!-- name -->
        <div class="field">
          <label for="name">Name <span class="required">*</span></label>
          <InputText
            id="name"
            v-model="moduleForm.name"
            placeholder="Module name"
            :invalid="submitted && !moduleForm.name"
          />
          <small v-if="submitted && !moduleForm.name" class="p-error">name is required</small>
        </div>

        <!-- Description -->
        <div class="field">
          <label for="description">Description</label>
          <Textarea
            id="description"
            v-model="moduleForm.description"
            placeholder="Module description"
            rows="2"
          />
        </div>

        <!-- Category -->
        <div class="field">
          <label for="category">Category <span class="required">*</span></label>
          <Select
            id="category"
            v-model="moduleForm.category"
            :options="categories"
            placeholder="Select category"
            :invalid="submitted && !moduleForm.category"
          />
          <small v-if="submitted && !moduleForm.category" class="p-error">Category is required</small>
        </div>

        <!-- Icon Upload -->
        <div class="field">
          <label>Icon (160x160)</label>
          <div v-if="iconPreview" class="icon-preview-container">
            <img :src="iconPreview" alt="Icon preview" class="icon-preview" />
            <Button
              icon="pi pi-times"
              severity="danger"
              size="small"
              rounded
              text
              @click="clearIcon"
              class="icon-remove-btn"
            />
          </div>
          <FileUpload
            v-else
            mode="basic"
            accept="image/*"
            :maxFileSize="1000000"
            @select="handleIconUpload"
            chooseLabel="Upload Icon"
            class="icon-upload"
          />
        </div>

        <Divider />

        <!-- Inputs Array Editor -->
        <div class="field">
          <div class="section-header">
            <label>Module Parameters</label>
            <Button
              label="Add Parameter"
              icon="pi pi-plus"
              size="small"
              @click="addInput"
            />
          </div>

          <div v-if="moduleForm.inputs.length === 0" class="empty-state">
            <i class="pi pi-inbox"></i>
            <p>No parameters defined</p>
          </div>

          <Accordion v-else value="0" class="inputs-accordion">
            <AccordionPanel
              v-for="(input, index) in moduleForm.inputs"
              :key="index"
              :value="String(index)"
            >
              <AccordionHeader>
                <div class="input-header">
                  <Tag :value="'ID: ' + input.id" severity="info" />
                  <strong class="input-label">{{ input.label || '' }}</strong>
                  <Tag v-if="input.required" value="Required" severity="danger" />
                  <Tag :value="input.type" severity="secondary" />
                  <Button
                    icon="pi pi-copy"
                    severity="info"
                    text
                    rounded
                    size="small"
                    @click.stop="copyParamVariable(index)"
                    v-tooltip.top="'Copy variable'"
                    class="copy-btn"
                  />
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="input-fields">
                  <div class="p-fluid">
                  <div class="field">
                    <label>Label <span class="required">*</span></label>
                    <InputText
                      v-model="input.label"
                      placeholder="Parameter label"
                      :invalid="submitted && !input.label"
                    />
                  </div>
                  <div class="field">
                    <label>Type <span class="required">*</span></label>
                    <Select
                      v-model="input.type"
                      :options="inputTypes"
                      optionLabel="label"
                      optionValue="value"
                      placeholder="Select type"
                    />
                  </div>
                  <div class="field-checkbox">
                    <Checkbox
                      v-model="input.required"
                      :inputId="`required-${index}`"
                      :binary="true"
                    />
                    <label :for="`required-${index}`">Required</label>
                  </div>
                  <div class="field">
                    <Button
                      label="Remove Parameter"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      size="small"
                      @click="removeInput(index)"
                    />
                  </div>
                </div>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
        </div>

        <!-- Link -->
        <div class="field">
          <label for="link">Data Collection API Endpoint</label>
          <InputText
            id="link"
            v-model="moduleForm.link"
            placeholder="/data"
            type="url"
          />
        </div>

        <!-- Error Message -->
        <Message v-if="error" severity="error" :closable="false">
          {{ error }}
        </Message>
      </div>

      <!-- Right: Code Editor -->
      <div class="editor-pane">
        <CodeCard
          v-model="moduleForm.payload"
          title="Payload"
          icon="pi pi-code"
          language="html"
          height="100%"
          :required="true"
          :error="submitted && !moduleForm.payload ? 'Payload is required' : ''"
        />
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        text
        @click="close"
        :disabled="loading"
      />
      <Button
        label="Preview"
        severity="info"
        icon="pi pi-eye"
        outlined
        @click="openPreview"
        :disabled="!moduleForm.payload"
      />
      <Button
        :label="mode === 'edit' ? 'Update' : 'Create'"
        icon="pi pi-check"
        @click="save"
        :loading="loading"
      />
    </template>
  </Dialog>

  <!-- Preview Dialog -->
  <Dialog
    v-model:visible="showPreviewDialog"
    modal
    header="Module Preview"
    :style="{ width: '90vw', maxWidth: '1400px', height: '90vh' }"
    :draggable="false"
  >
    <div class="preview-container">
      <div class="preview-header">
        <div class="preview-info">
          <strong>{{ moduleForm.name || 'Untitled Module' }}</strong>
          <span v-if="moduleForm.description">{{ moduleForm.description }}</span>
        </div>
      </div>

      <div class="preview-frame">
        <iframe
          :srcdoc="moduleForm.payload"
          sandbox="allow-scripts allow-forms"
          class="preview-iframe"
        ></iframe>
      </div>
    </div>

    <template #footer>
      <Button label="Close" severity="secondary" text @click="showPreviewDialog = false" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import CodeCard from '@/components/default/CodeCard.vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import FileUpload from 'primevue/fileupload'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const toast = useToast()

const props = defineProps({
  modelValue: Boolean,
  mode: {
    type: String,
    default: 'create'
  },
  module: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'save'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const error = ref(null)
const submitted = ref(false)
const iconPreview = ref(null)
const showPreviewDialog = ref(false)

const moduleForm = ref({
  id: null,
  name: '',
  description: '',
  category: 'Custom',
  icon: '',
  inputs: [],
  payload: '',
  link: ''
})

const categories = [
  'Initial Access',
  'Execution',
  'Persistence',
  'Privilege Escalation',
  'Credential Access',
  'Discovery',
  'Lateral Movement',
  'Collection',
  'Exfiltration',
  'Command & Control',
  'Post Exploitation',
  'Social Engineering',
  'Browser Exploitation',
  'Cross-Site Scripting',
  'Clickjacking',
  'Custom'
]

const inputTypes = [
  { label: 'String', value: 'string' },
  { label: 'Number', value: 'number' },
  { label: 'Boolean', value: 'boolean' },
  { label: 'Text Area', value: 'textarea' }
]

const defaultHtmlTemplate = `// Module HTML Payload
// Access parameters via: params[0], params[1], etc.
<div>
  <h1>Hello from the module!</h1>
  <p>This is a sample HTML payload. You can use the provided parameters to customize the content.</p>
</div>
`

// Watch for dialog open/close
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    if (props.mode === 'edit' && props.module) {
      moduleForm.value = {
        ...props.module,
        inputs: props.module.inputs ? JSON.parse(JSON.stringify(props.module.inputs)) : []
      }
      iconPreview.value = props.module.icon || null
    } else {
      resetForm()
    }
    submitted.value = false
    error.value = null
  }
})

function resetForm() {
  moduleForm.value = {
    id: null,
    name: '',
    description: '',
    category: 'Custom',
    icon: '',
    inputs: [],
    payload: defaultHtmlTemplate,
    link: ''
  }
  iconPreview.value = null
}

function addInput() {
  const nextId = moduleForm.value.inputs.length > 0
    ? Math.max(...moduleForm.value.inputs.map(i => i.id)) + 1
    : 0

  moduleForm.value.inputs.push({
    id: nextId,
    label: '',
    type: 'string',
    required: false,
    options: []
  })
}

function removeInput(index) {
  moduleForm.value.inputs.splice(index, 1)
}
function handleIconUpload(event) {
  const file = event.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const img = new Image()
    img.onload = () => {
      // Resize to 160x160
      const canvas = document.createElement('canvas')
      canvas.width = 160
      canvas.height = 160
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, 160, 160)

      const base64 = canvas.toDataURL('image/png')
      moduleForm.value.icon = base64
      iconPreview.value = base64
    }
    img.src = e.target.result
  }
  reader.readAsDataURL(file)
}

function clearIcon() {
  moduleForm.value.icon = ''
  iconPreview.value = null
}

async function copyParamVariable(index) {
  const variable = `{{ params[${index}] }}`
  try {
    await navigator.clipboard.writeText(variable)
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: `${variable} copied to clipboard`,
      life: 2000
    })
  } catch (error) {
    console.error('Failed to copy:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy to clipboard',
      life: 2000
    })
  }
}

function validateForm() {
  if (!moduleForm.value.name || !moduleForm.value.category || !moduleForm.value.payload) {
    return false
  }

  // Validate inputs
  for (const input of moduleForm.value.inputs) {
    if (input.id === null || !input.label || !input.type) {
      return false
    }
  }

  return true
}

function save() {
  submitted.value = true
  error.value = null

  if (!validateForm()) {
    return
  }

  emit('save', { ...moduleForm.value })
}

function close() {
  visible.value = false
}

function openPreview() {
  if (!moduleForm.value.payload) return
  showPreviewDialog.value = true
}

function handleJsonImport(event) {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const json = JSON.parse(e.target.result)

      // Validate JSON structure
      if (!json.name || !json.payload) {
        throw new Error('Invalid module JSON: missing required fields (name, payload)')
      }

      // Populate form
      moduleForm.value = {
        id: null, // Always create new module on import
        name: json.name || '',
        description: json.description || '',
        category: json.category || 'Custom',
        icon: json.icon || '',
        inputs: json.inputs ? JSON.parse(JSON.stringify(json.inputs)) : [],
        payload: json.payload || '',
        link: json.link || ''
      }

      iconPreview.value = json.icon || null

      toast.add({
        severity: 'success',
        summary: 'Module Imported',
        detail: `Module "${json.name}" loaded successfully`,
        life: 3000
      })
    } catch (error) {
      console.error('JSON import error:', error)
      toast.add({
        severity: 'error',
        summary: 'Import Failed',
        detail: error.message || 'Invalid JSON file',
        life: 4000
      })
    }
  }
  reader.readAsText(file)

  // Reset input so same file can be imported again
  event.target.value = ''
}
</script>

<style scoped>
/* Dialog header */
.dialog-header-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 1rem;
}

.dialog-title {
  font-size: 1.25rem;
  font-weight: 600;
}

/* Layout */
.dialog-layout {
  display: grid;
  flex: 1;
  grid-template-columns: 400px 1fr;
  gap: 1.5rem;
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.editor-pane {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.settings-sidebar {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.editor-pane :deep(.code-card) {
  min-height: 0;
  height: 100%;
}

.editor-pane :deep(.code-card-body) {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.required {
  color: var(--red-500);
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.section-header label {
  font-weight: 600;
  font-size: 1rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: 0.5rem;
  display: block;
}

.icon-preview-container {
  position: relative;
  display: inline-block;
  border: 2px solid var(--primary-color);
  border-radius: 8px;
  padding: 8px;
}

.icon-preview {
  display: block;
  width: 160px;
  height: 160px;
  border-radius: 4px;
}

.icon-remove-btn {
  position: absolute;
  top: -8px;
  right: -8px;
}

.input-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  min-width: 0;
  flex-wrap: nowrap;
}

.input-header :deep(.p-tag) {
  flex-shrink: 0;
}

.input-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn {
  margin-left: auto;
}

.input-fields {
  padding: 0.5rem 0;
}

.inputs-accordion {
  margin-top: 0.5rem;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.field-checkbox label {
  margin: 0;
}

/* Preview Dialog */
.preview-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: calc(90vh - 160px);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.preview-info strong {
  color: var(--color-heading);
}

.preview-info span {
  color: var(--color-text-mute);
  font-size: 0.875rem;
}

.preview-frame {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-background);
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

@media (max-width: 1200px) {
  .dialog-layout {
    grid-template-columns: 280px minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .dialog-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .settings-sidebar {
    padding-right: 0;
  }
}
</style>
