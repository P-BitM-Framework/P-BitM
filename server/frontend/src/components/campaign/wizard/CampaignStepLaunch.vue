<template>
  <div class="field">
    <label for="targetList">Target List <span class="required">*</span></label>
    <Select
      id="targetList"
      v-model="form.target_list_id"
      :options="targetLists"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Target List"
      :invalid="submitted && !form.target_list_id"
      :loading="loadingTargets"
    >
      <template #value="slotProps">
        <div v-if="slotProps.value" class="select-value">
          <i class="pi pi-users"></i>
          <span>{{ getTargetListName(slotProps.value) }}</span>
        </div>
        <span v-else>Select Target List</span>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <i class="pi pi-users"></i>
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small>{{ slotProps.option.total_targets || 0 }} targets</small>
          </div>
        </div>
      </template>
    </Select>
    <small v-if="submitted && !form.target_list_id" class="p-error">Target List is required</small>
    <small v-if="targetLists.length === 0" class="text-muted">
      No target lists available.
      <a href="#" @click.prevent="$router.push({ name: 'target-lists' })">Create one first</a>
    </small>
  </div>

  <div class="field">
    <label for="url">URL to Clone <span class="required">*</span></label>
    <InputText
      id="url"
      v-model="form.url"
      type="url"
      placeholder="https://example.com"
      :invalid="submitted && !isValidSourceUrl"
    />
    <small v-if="submitted && !isValidSourceUrl" class="p-error">
      {{ sourceUrlError }}
    </small>
  </div>

  <div class="field">
    <label for="tracking-parameter">Tracking Parameter</label>
    <InputText
      id="tracking-parameter"
      v-model.trim="form.trackingParameter"
      maxlength="32"
      placeholder="Optional, for example state"
      :invalid="submitted && !isValidTrackingParameter"
    />
    <small
      v-if="submitted && !isValidTrackingParameter"
      class="p-error"
    >
      Use a letter first, followed only by letters, numbers, _ or -.
    </small>
    <small class="text-muted">
      Leave empty to place the opaque token in the URL path.
    </small>
  </div>

  <div class="grid-field" v-if="!isStandalone">
    <div class="field">
      <label for="scheduledDate">Email Sending Start <span class="required">*</span></label>
      <DatePicker
        id="scheduledDate"
        v-model="form.scheduled_date"
        :minDate="new Date()"
        showTime
        hourFormat="24"
        dateFormat="dd/mm/yy"
        inputId="start_date"
        showIcon
        iconDisplay="input"
        variant="filled"
        placeholder="Select start date"
        :invalid="submitted && !form.scheduled_date"
      />
      <small v-if="submitted && !form.scheduled_date" class="p-error">
        Email sending start is required
      </small>
    </div>

    <div class="field">
      <label for="scheduledDateEnd">Email Sending End <span class="required">*</span></label>
      <DatePicker
        id="scheduledDateEnd"
        v-model="form.scheduled_date_end"
        :minDate="form.scheduled_date || new Date()"
        showTime
        hourFormat="24"
        dateFormat="dd/mm/yy"
        inputId="end_date"
        showIcon
        iconDisplay="input"
        variant="filled"
        placeholder="Select end date"
        :invalid="submitted && !hasValidSchedule"
      />
      <small v-if="submitted && !hasValidSchedule" class="p-error">
        Start must be in the future and end must be later than start
      </small>
    </div>
  </div>

  <div class="advanced-toggle">
    <Button
      @click="showAdvanced = !showAdvanced"
      severity="secondary"
      text
      size="small"
    >
      <i :class="showAdvanced ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"></i>
      Advanced Options
    </Button>
  </div>

  <div v-if="showAdvanced" class="advanced-options">
    <div class="option-group">
      <label class="option-label">Protocol</label>
      <div class="protocol-selector">
        <Button
          :severity="form.protocol === 'vnc' ? 'primary' : 'secondary'"
          @click="form.protocol = 'vnc'"
          size="small"
          class="protocol-button"
        >
          VNC
        </Button>
        <Button
          :severity="form.protocol === 'selkies' ? 'primary' : 'secondary'"
          @click="form.protocol = 'selkies'"
          size="small"
          class="protocol-button"
        >
          Selkies
        </Button>
      </div>
    </div>

    <Message v-if="form.protocol === 'selkies'" severity="warn" :closable="false">
      <span class="warning-text">
        ⚠️ <strong>Warning:</strong> High quality and lossless settings may cause client memory exhaustion.
        Configure values carefully based on your infrastructure.
      </span>
    </Message>

    <div v-if="form.protocol === 'selkies'" class="selkies-options">
      <div class="option-group">
        <label class="option-label">Features</label>
        <div class="checkbox-group">
          <div class="p-field-checkbox">
            <Checkbox v-model="form.useStreamingMode" :binary="true" inputId="streaming" />
            <label for="streaming">Enable Streaming Mode (lower latency)</label>
          </div>
          <div class="p-field-checkbox">
            <Checkbox v-model="form.usePaintOverQuality" :binary="true" inputId="paintover" />
            <label for="paintover">Use Paint Over Quality (burst quality on interactions)</label>
          </div>
        </div>
      </div>

      <Divider />

      <div class="option-group">
        <label class="option-label">Video Quality</label>
        <div class="custom-button-group">
          <button
            type="button"
            @click="form.videoQuality = 'low'"
            :class="['custom-option-btn', 'quality-low', { 'selected': form.videoQuality === 'low' }]"
          >
            Low
          </button>
          <button
            type="button"
            @click="form.videoQuality = 'medium'"
            :class="['custom-option-btn', 'quality-medium', { 'selected': form.videoQuality === 'medium' }]"
          >
            Medium
          </button>
          <button
            type="button"
            @click="form.videoQuality = 'high'"
            :class="['custom-option-btn', 'quality-high', { 'selected': form.videoQuality === 'high' }]"
          >
            High
          </button>
        </div>
        <small class="option-hint">Controls overall video encoding quality</small>
      </div>

      <div class="option-group">
        <label class="option-label">Framerate</label>
        <div class="custom-button-group">
          <button
            type="button"
            @click="form.framerate = 'low'"
            :class="['custom-option-btn', 'quality-low', { 'selected': form.framerate === 'low' }]"
          >
            Low (30fps)
          </button>
          <button
            type="button"
            @click="form.framerate = 'medium'"
            :class="['custom-option-btn', 'quality-medium', { 'selected': form.framerate === 'medium' }]"
          >
            Medium (60fps)
          </button>
          <button
            type="button"
            @click="form.framerate = 'high'"
            :class="['custom-option-btn', 'quality-high', { 'selected': form.framerate === 'high' }]"
          >
            High (120fps)
          </button>
        </div>
        <small class="option-hint">Higher values = smoother but more bandwidth</small>
      </div>

      <div class="option-group">
        <label class="option-label">Compression Level</label>
        <div class="custom-button-group">
          <button
            type="button"
            @click="form.compressionLevel = 'low'"
            :class="['custom-option-btn', 'quality-low', { 'selected': form.compressionLevel === 'low' }]"
          >
            Low
          </button>
          <button
            type="button"
            @click="form.compressionLevel = 'medium'"
            :class="['custom-option-btn', 'quality-medium', { 'selected': form.compressionLevel === 'medium' }]"
          >
            Medium
          </button>
          <button
            type="button"
            @click="form.compressionLevel = 'high'"
            :class="['custom-option-btn', 'quality-high', { 'selected': form.compressionLevel === 'high' }]"
          >
            High
          </button>
        </div>
        <small class="option-hint">Lower = smaller file size, higher = better quality</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'

defineProps({
  form: { type: Object, required: true },
  submitted: { type: Boolean, default: false },
  isStandalone: { type: Boolean, default: false },
  targetLists: { type: Array, required: true },
  loadingTargets: { type: Boolean, default: false },
  getTargetListName: { type: Function, required: true },
  isValidSourceUrl: { type: Boolean, default: false },
  sourceUrlError: { type: String, default: 'Enter a complete HTTP or HTTPS URL' },
  isValidTrackingParameter: { type: Boolean, default: true },
  hasValidSchedule: { type: Boolean, default: true }
})

const showAdvanced = defineModel('showAdvanced', { type: Boolean, default: false })
</script>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--color-heading);
}

.p-error {
  color: var(--red-500);
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.required {
  color: var(--red-500);
}

.text-muted {
  color: var(--color-text-mute);
  font-size: 0.813rem;
}

.text-muted a {
  color: var(--primary-color);
  text-decoration: none;
}

.text-muted a:hover {
  text-decoration: underline;
}

.select-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.select-value i {
  color: var(--color-text-mute);
  font-size: 0.9rem;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.select-option i {
  color: var(--color-text-mute);
  font-size: 1rem;
  min-width: 20px;
}

.option-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.option-info strong {
  font-size: 0.9rem;
  color: var(--color-heading);
}

.option-info small {
  font-size: 0.813rem;
  color: var(--color-text-mute);
}

.grid-field {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.advanced-toggle {
  display: flex;
  justify-content: flex-start;
  margin-top: 0.5rem;
}

.advanced-options {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.option-label {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-color);
}

.option-hint {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  margin-top: -0.25rem;
}

.protocol-selector {
  display: flex;
  gap: 1rem;
}

.protocol-button {
  flex: 1;
  max-width: 200px;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-left: 0.5rem;
}

.p-field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.p-field-checkbox label {
  margin-bottom: 0;
  cursor: pointer;
  font-size: 0.9rem;
}

.selkies-options {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.warning-text {
  font-size: 0.9rem;
  line-height: 1.5;
}

.custom-button-group {
  display: flex;
  gap: 0.5rem;
}

.custom-option-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid transparent;
  border-radius: 6px;
  background: var(--surface-100);
  color: var(--text-color);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-interactive);
  outline: none;
}

.custom-option-btn.quality-low:not(.selected):hover {
  background: var(--surface-200);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--success) 20%, transparent);
  transform: translateY(-2px);
}

.custom-option-btn.quality-medium:not(.selected):hover {
  background: var(--surface-200);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--warning) 20%, transparent);
  transform: translateY(-2px);
}

.custom-option-btn.quality-high:not(.selected):hover {
  background: var(--surface-200);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--danger) 20%, transparent);
  transform: translateY(-2px);
}

.custom-option-btn.quality-low.selected {
  background: var(--success);
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--success) 30%, transparent);
}

.custom-option-btn.quality-low.selected:hover {
  background: color-mix(in srgb, var(--success) 82%, black);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--success) 40%, transparent);
  transform: translateY(-1px);
}

.custom-option-btn.quality-medium.selected {
  background: var(--warning);
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--warning) 30%, transparent);
}

.custom-option-btn.quality-medium.selected:hover {
  background: color-mix(in srgb, var(--warning) 82%, black);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--warning) 40%, transparent);
  transform: translateY(-1px);
}

.custom-option-btn.quality-high.selected {
  background: var(--danger);
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--danger) 30%, transparent);
}

.custom-option-btn.quality-high.selected:hover {
  background: color-mix(in srgb, var(--danger) 82%, black);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--danger) 40%, transparent);
  transform: translateY(-1px);
}

.custom-option-btn:active {
  transform: translateY(0);
}

.custom-option-btn:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
</style>
