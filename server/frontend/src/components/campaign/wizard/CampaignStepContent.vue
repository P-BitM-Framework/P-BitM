<template>
  <div class="field" v-if="!isStandalone">
    <label for="smtpProfile">SMTP Profile <span class="required">*</span></label>
    <Select
      id="smtpProfile"
      v-model="form.smtp_profile_id"
      :options="smtpProfiles"
      optionLabel="name"
      optionValue="id"
      placeholder="Select SMTP Profile"
      :invalid="submitted && !form.smtp_profile_id"
      :loading="loadingProfiles"
    >
      <template #value="slotProps">
        <div v-if="slotProps.value" class="select-value">
          <i class="pi pi-server"></i>
          <span>{{ getSmtpProfileName(slotProps.value) }}</span>
        </div>
        <span v-else>Select SMTP Profile</span>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <i class="pi pi-server"></i>
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small>{{ slotProps.option.smtp_host }}:{{ slotProps.option.smtp_port }}</small>
          </div>
        </div>
      </template>
    </Select>
    <small v-if="submitted && !form.smtp_profile_id" class="p-error">SMTP Profile is required</small>
    <small v-if="smtpProfiles.length === 0" class="text-muted">
      No SMTP profiles available.
      <a href="#" @click.prevent="$router.push({ name: 'smtp-profiles' })">Create one first</a>
    </small>
  </div>

  <div class="field" v-if="!isStandalone">
    <label for="emailTemplate">Email Template <span class="required">*</span></label>
    <Select
      id="emailTemplate"
      v-model="form.email_template_id"
      :options="emailTemplates"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Email Template"
      :invalid="submitted && !form.email_template_id"
      :loading="loadingTemplates"
    >
      <template #value="slotProps">
        <div v-if="slotProps.value" class="select-value">
          <i class="pi pi-file"></i>
          <span>{{ getEmailTemplateName(slotProps.value) }}</span>
        </div>
        <span v-else>Select Email Template</span>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <i class="pi pi-file"></i>
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small>{{ slotProps.option.subject }}</small>
          </div>
        </div>
      </template>
    </Select>
    <small v-if="submitted && !form.email_template_id" class="p-error">Email Template is required</small>
    <small v-if="emailTemplates.length === 0" class="text-muted">
      No email templates available.
      <a href="#" @click.prevent="$router.push({ name: 'email-templates' })">Create one first</a>
    </small>
  </div>

  <div class="field">
    <label for="landingPage">Landing Page <span class="required">*</span></label>
    <Select
      id="landingPage"
      v-model="form.landing_page_id"
      :options="landingPages"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Landing Page"
      :invalid="submitted && !form.landing_page_id"
      :loading="loadingLandingPages"
    >
      <template #value="slotProps">
        <div v-if="slotProps.value" class="select-value">
          <i class="pi pi-globe"></i>
          <span>{{ getLandingPageName(slotProps.value) }}</span>
        </div>
        <span v-else>Select Landing Page</span>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <i class="pi pi-globe"></i>
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small v-if="slotProps.option.url">{{ slotProps.option.url }}</small>
          </div>
        </div>
      </template>
    </Select>
    <small v-if="submitted && !form.landing_page_id" class="p-error">Landing Page is required</small>
    <small v-if="landingPages.length === 0" class="text-muted">
      No landing pages available.
      <a href="#" @click.prevent="$router.push({ name: 'landing-pages' })">Create one first</a>
    </small>
  </div>

  <div class="field">
    <label for="plugins">Plugins</label>
    <MultiSelect
      id="plugins"
      v-model="form.plugin_ids"
      :options="availablePlugins"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Plugins (optional)"
      display="chip"
      :maxSelectedLabels="3"
      :loading="loadingPlugins"
    >
      <template #value="slotProps">
        <template v-if="!slotProps.value || slotProps.value.length === 0">
          <span class="text-muted">No plugins selected</span>
        </template>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <Icon icon="mdi:firefox" />
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small v-if="slotProps.option.description">{{ slotProps.option.description }}</small>
          </div>
        </div>
      </template>
    </MultiSelect>
    <small class="text-muted">
      Select plugins to inject into the campaign (leave empty for none)
    </small>

    <div v-if="form.plugin_ids && form.plugin_ids.length > 0" class="selected-plugins">
      <div class="plugins-header">
        <strong>Selected Plugins ({{ form.plugin_ids.length }}):</strong>
      </div>
      <div class="plugin-chips">
        <Chip
          v-for="pluginId in form.plugin_ids"
          :key="pluginId"
          :label="getPluginName(pluginId)"
          removable
          @remove="$emit('remove-plugin', pluginId)"
        >
          <template #icon>
            <Icon icon="mdi:firefox" />
          </template>
        </Chip>
      </div>
    </div>
  </div>

  <div class="field">
    <label for="attacks">Modules</label>
    <MultiSelect
      id="attacks"
      v-model="form.module_ids"
      :options="availableAttacks"
      optionLabel="name"
      optionValue="id"
      placeholder="Select Modules (optional)"
      display="chip"
      :maxSelectedLabels="3"
      :loading="loadingAttacks"
    >
      <template #value="slotProps">
        <template v-if="!slotProps.value || slotProps.value.length === 0">
          <span class="text-muted">No modules selected</span>
        </template>
      </template>
      <template #option="slotProps">
        <div class="select-option">
          <i class="pi pi-bolt"></i>
          <div class="option-info">
            <strong>{{ slotProps.option.name }}</strong>
            <small v-if="slotProps.option.description">{{ slotProps.option.description }}</small>
            <Tag
              v-if="slotProps.option.inputs && slotProps.option.inputs.length > 0"
              :value="`${slotProps.option.inputs.length} params`"
              severity="info"
              class="ml-2"
              style="font-size: 0.65rem; padding: 0.15rem 0.35rem;"
            />
          </div>
        </div>
      </template>
    </MultiSelect>
    <small class="text-muted">
      Select Modules to deploy in the campaign (leave empty for none)
    </small>

    <div v-if="form.module_ids && form.module_ids.length > 0" class="selected-plugins">
      <div class="plugins-header">
        <strong>Selected Modules ({{ form.module_ids.length }}):</strong>
      </div>
      <div class="plugin-chips">
        <Chip
          v-for="attackId in form.module_ids"
          :key="attackId"
          :label="getAttackName(attackId)"
          removable
          @remove="$emit('remove-attack', attackId)"
        >
          <template #icon>
            <i class="pi pi-bolt"></i>
          </template>
        </Chip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'

defineProps({
  form: { type: Object, required: true },
  submitted: { type: Boolean, default: false },
  isStandalone: { type: Boolean, default: false },
  smtpProfiles: { type: Array, required: true },
  loadingProfiles: { type: Boolean, default: false },
  emailTemplates: { type: Array, required: true },
  loadingTemplates: { type: Boolean, default: false },
  landingPages: { type: Array, required: true },
  loadingLandingPages: { type: Boolean, default: false },
  availablePlugins: { type: Array, required: true },
  loadingPlugins: { type: Boolean, default: false },
  availableAttacks: { type: Array, required: true },
  loadingAttacks: { type: Boolean, default: false },
  getSmtpProfileName: { type: Function, required: true },
  getEmailTemplateName: { type: Function, required: true },
  getLandingPageName: { type: Function, required: true },
  getPluginName: { type: Function, required: true },
  getAttackName: { type: Function, required: true }
})

defineEmits(['remove-plugin', 'remove-attack'])
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

.selected-plugins {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  border: 1px solid var(--surface-200);
}

.plugins-header {
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color);
}

.plugin-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .plugin-chips {
    flex-direction: column;
  }
}
</style>
