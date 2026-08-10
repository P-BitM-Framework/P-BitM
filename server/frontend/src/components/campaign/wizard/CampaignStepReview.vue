<template>
  <div class="review-heading">
    <div>
      <h3>Review configuration</h3>
      <p>Verify the campaign settings before creation.</p>
    </div>
    <Tag :value="isStandalone ? 'Standalone' : 'Complete'" severity="info" />
  </div>

  <div class="review-grid">
    <div class="review-section">
      <h4><i class="pi pi-flag"></i> Campaign</h4>
      <dl>
        <div><dt>Name</dt><dd>{{ form.name }}</dd></div>
        <div><dt>Public hostname</dt><dd>{{ form.public_domain || 'Environment default' }}</dd></div>
        <div><dt>Source URL</dt><dd>{{ form.url }}</dd></div>
        <div><dt>Protocol</dt><dd>{{ form.protocol === 'selkies' ? 'Selkies' : 'VNC' }}</dd></div>
        <div>
          <dt>Tracking token</dt>
          <dd>{{ form.trackingParameter ? `Query parameter: ${form.trackingParameter}` : 'URL path (default)' }}</dd>
        </div>
      </dl>
    </div>

    <div class="review-section">
      <h4><i class="pi pi-file"></i> Content</h4>
      <dl>
        <div v-if="!isStandalone"><dt>SMTP</dt><dd>{{ getSmtpProfileName(form.smtp_profile_id) }}</dd></div>
        <div v-if="!isStandalone"><dt>Email</dt><dd>{{ getEmailTemplateName(form.email_template_id) }}</dd></div>
        <div><dt>Landing page</dt><dd>{{ getLandingPageName(form.landing_page_id) }}</dd></div>
        <div><dt>Target list</dt><dd>{{ getTargetListName(form.target_list_id) }}</dd></div>
      </dl>
    </div>

    <div class="review-section">
      <h4><i class="pi pi-bolt"></i> Attack Vectors</h4>
      <dl>
        <div><dt>Extensions</dt><dd>{{ form.plugin_ids.length ? form.plugin_ids.map(getPluginName).join(', ') : 'None' }}</dd></div>
        <div><dt>Modules</dt><dd>{{ form.module_ids.length ? form.module_ids.map(getAttackName).join(', ') : 'None' }}</dd></div>
      </dl>
    </div>

    <div class="review-section">
      <h4><i class="pi pi-calendar"></i> Launch</h4>
      <dl>
        <div><dt>Mode</dt><dd>{{ isStandalone ? 'Immediate' : 'Scheduled' }}</dd></div>
        <div v-if="!isStandalone"><dt>Sending starts</dt><dd>{{ formatReviewDate(form.scheduled_date) }}</dd></div>
        <div v-if="!isStandalone"><dt>Sending ends</dt><dd>{{ formatReviewDate(form.scheduled_date_end) }}</dd></div>
      </dl>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
  isStandalone: { type: Boolean, default: false },
  getSmtpProfileName: { type: Function, required: true },
  getEmailTemplateName: { type: Function, required: true },
  getLandingPageName: { type: Function, required: true },
  getTargetListName: { type: Function, required: true },
  getPluginName: { type: Function, required: true },
  getAttackName: { type: Function, required: true },
  formatReviewDate: { type: Function, required: true }
})
</script>

<style scoped>
.review-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.review-heading h3,
.review-heading p {
  margin: 0;
}

.review-heading h3 {
  color: var(--color-heading);
  font-size: 1.2rem;
  font-weight: 600;
}

.review-heading p {
  margin-top: 0.25rem;
  color: var(--color-text-mute);
  font-size: 0.875rem;
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.review-section {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background-mute);
}

.review-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.85rem;
  color: var(--color-heading);
  font-size: 0.9rem;
  font-weight: 600;
}

.review-section dl {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0;
}

.review-section dl > div {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 0.75rem;
}

.review-section dt {
  color: var(--color-text-mute);
  font-size: 0.78rem;
}

.review-section dd {
  overflow-wrap: anywhere;
  margin: 0;
  color: var(--color-text);
  font-size: 0.82rem;
}
</style>
