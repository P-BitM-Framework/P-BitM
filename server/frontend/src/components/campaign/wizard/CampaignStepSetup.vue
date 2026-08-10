<template>
  <div class="field">
    <label for="campaignName">Campaign Name <span class="required">*</span></label>
    <InputText
      id="campaignName"
      v-model="form.name"
      placeholder="Q1 2026 Phishing Campaign"
      :invalid="submitted && !form.name"
    />
    <small v-if="submitted && !form.name" class="p-error">Campaign name is required</small>
  </div>

  <div class="field">
    <label for="description">Description</label>
    <Textarea
      id="description"
      v-model="form.description"
      rows="3"
      placeholder="Brief description of this campaign..."
    />
  </div>

  <div class="field">
    <label for="publicDomain">Campaign Domain</label>
    <InputText
      id="publicDomain"
      v-model="form.public_domain"
      placeholder="campaign.example.com"
      :invalid="submitted && !isValidHostname"
    />
    <small v-if="submitted && !isValidHostname" class="p-error">
      Enter a hostname without protocol, path, or trailing slash
    </small>
    <small class="text-muted">
      Leave empty in test. In production this becomes the hostname exposed by Traefik.
    </small>
  </div>

  <div class="field">
    <label>Campaign Type</label>
    <SelectButton
      v-model="form.campaign_type"
      :options="campaignTypeOptions"
      optionLabel="label"
      optionValue="value"
    />
    <small class="text-muted">
      Standalone creates per-victim links without SMTP or scheduling.
    </small>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
  submitted: { type: Boolean, default: false },
  isValidHostname: { type: Boolean, default: true },
  campaignTypeOptions: { type: Array, required: true }
})
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
</style>
