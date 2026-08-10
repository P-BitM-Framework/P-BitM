<template>
  <div class="new-campaign-form">
    <template v-if="creating">
      <div class="creating-loader">
        <template v-if="!created">
          <i class="pi pi-spin pi-spinner launch-state-icon launch-state-icon--loading"></i>
          <p class="loader-text">Creating campaign...</p>
        </template>
        <template v-else>
          <i class="pi pi-check-circle launch-state-icon launch-state-icon--success"></i>
          <p class="success-text">Campaign created!</p>
        </template>
      </div>
    </template>

    <template v-else>
      <ol class="wizard-progress" aria-label="Campaign creation progress">
        <li
          v-for="(step, index) in wizardSteps"
          :key="step.label"
          :class="{ active: currentStep === index, complete: currentStep > index }"
        >
          <button
            type="button"
            :disabled="index > currentStep"
            :aria-current="currentStep === index ? 'step' : undefined"
            :aria-label="`${step.label}: ${step.description}`"
            @click="goToStep(index)"
          >
            <span class="step-number">
              <i v-if="currentStep > index" class="pi pi-check"></i>
              <template v-else>{{ index + 1 }}</template>
            </span>
            <span class="step-copy">
              <strong>{{ step.label }}</strong>
              <small>{{ step.description }}</small>
            </span>
          </button>
        </li>
      </ol>

      <div class="form-grid">
        <Transition name="fade" mode="out-in">
          <section v-if="currentStep === 0" key="0" class="wizard-step-panel">
            <CampaignStepSetup
              :form="form"
              :submitted="submitted"
              :is-valid-hostname="isValidHostname"
              :campaign-type-options="campaignTypeOptions"
            />
          </section>

          <section v-else-if="currentStep === 1" key="1" class="wizard-step-panel">
            <CampaignStepContent
              :form="form"
              :submitted="submitted"
              :is-standalone="isStandalone"
              :smtp-profiles="smtpProfiles"
              :loading-profiles="loadingProfiles"
              :email-templates="emailTemplates"
              :loading-templates="loadingTemplates"
              :landing-pages="landingPages"
              :loading-landing-pages="loadingLandingPages"
              :available-plugins="availablePlugins"
              :loading-plugins="loadingPlugins"
              :available-attacks="availableAttacks"
              :loading-attacks="loadingAttacks"
              :get-smtp-profile-name="getSmtpProfileName"
              :get-email-template-name="getEmailTemplateName"
              :get-landing-page-name="getLandingPageName"
              :get-plugin-name="getPluginName"
              :get-attack-name="getAttackName"
              @remove-plugin="removePlugin"
              @remove-attack="removeAttack"
            />
          </section>

          <section v-else-if="currentStep === 2" key="2" class="wizard-step-panel">
            <CampaignStepLaunch
              :form="form"
              :submitted="submitted"
              :is-standalone="isStandalone"
              :target-lists="targetLists"
              :loading-targets="loadingTargets"
              :get-target-list-name="getTargetListName"
              :is-valid-source-url="isValidSourceUrl"
              :source-url-error="sourceUrlError"
              :is-valid-tracking-parameter="isValidTrackingParameter"
              :has-valid-schedule="hasValidSchedule"
              v-model:show-advanced="showAdvanced"
            />
          </section>

          <section v-else key="3" class="wizard-step-panel review-panel">
            <CampaignStepReview
              :form="form"
              :is-standalone="isStandalone"
              :get-smtp-profile-name="getSmtpProfileName"
              :get-email-template-name="getEmailTemplateName"
              :get-landing-page-name="getLandingPageName"
              :get-target-list-name="getTargetListName"
              :get-plugin-name="getPluginName"
              :get-attack-name="getAttackName"
              :format-review-date="formatReviewDate"
            />
          </section>
        </Transition>
      </div>

      <div class="form-footer">
        <Button label="Cancel" severity="secondary" text @click="closeDialog" />
        <div class="footer-navigation">
          <Button
            v-if="currentStep > 0"
            label="Back"
            icon="pi pi-arrow-left"
            severity="secondary"
            outlined
            @click="previousStep"
          />
          <Button
            v-if="currentStep < wizardSteps.length - 1"
            label="Continue"
            icon="pi pi-arrow-right"
            iconPos="right"
            @click="nextStep"
          />
          <Button
            v-else
            label="Create Campaign"
            icon="pi pi-check"
            :loading="creating"
            @click="createCampaign"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useCampaignWizard } from '@/composables/useCampaignWizard'
import CampaignStepSetup from './wizard/CampaignStepSetup.vue'
import CampaignStepContent from './wizard/CampaignStepContent.vue'
import CampaignStepLaunch from './wizard/CampaignStepLaunch.vue'
import CampaignStepReview from './wizard/CampaignStepReview.vue'

defineProps({
  visible: Boolean
})

const emit = defineEmits(['campaign-created', 'creating-changed', 'cancel'])

const {
  wizardSteps,
  campaignTypeOptions,
  creating,
  created,
  submitted,
  showAdvanced,
  currentStep,
  loadingProfiles,
  loadingTemplates,
  loadingTargets,
  loadingLandingPages,
  loadingPlugins,
  loadingAttacks,
  smtpProfiles,
  emailTemplates,
  targetLists,
  landingPages,
  availablePlugins,
  availableAttacks,
  form,
  isStandalone,
  isValidHostname,
  isValidSourceUrl,
  sourceUrlError,
  isValidTrackingParameter,
  hasValidSchedule,
  fetchReferenceData,
  getSmtpProfileName,
  getEmailTemplateName,
  getLandingPageName,
  getPluginName,
  getAttackName,
  getTargetListName,
  removePlugin,
  removeAttack,
  nextStep,
  previousStep,
  goToStep,
  formatReviewDate,
  createCampaign,
  closeDialog
} = useCampaignWizard(emit)

onMounted(fetchReferenceData)
</script>

<style scoped>
.new-campaign-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.wizard-progress {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  margin: 0;
  padding: 1rem 0.75rem 1.1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-background-soft);
  list-style: none;
}

.wizard-progress li {
  position: relative;
  min-width: 0;
}

.wizard-progress li:not(:last-child)::after {
  content: '';
  position: absolute;
  z-index: 0;
  top: 18px;
  right: calc(-50% + 27px);
  left: calc(50% + 27px);
  height: 2px;
  background: var(--color-border);
  pointer-events: none;
}

.wizard-progress li.complete:not(:last-child)::after {
  background: var(--color-accent);
}

.wizard-progress button {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  min-width: 0;
  padding: 0 0.75rem;
  border: 0;
  background: transparent;
  color: var(--color-text-mute);
  text-align: center;
}

.wizard-progress button:not(:disabled) {
  cursor: pointer;
}

.wizard-progress button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 5px;
  border-radius: var(--radius-sm);
}

.wizard-progress li.active button,
.wizard-progress li.complete button {
  color: var(--color-heading);
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-background-soft);
  box-shadow: 0 0 0 6px var(--color-background-soft);
  font-size: 0.82rem;
  font-weight: 700;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.wizard-progress li.active .step-number,
.wizard-progress li.complete .step-number {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: white;
}

.wizard-progress li.active .step-number {
  box-shadow:
    0 0 0 6px var(--color-background-soft),
    0 0 0 9px var(--color-accent-subtle);
}

.wizard-progress li.complete button:hover .step-number {
  background: var(--color-accent-soft);
}

.step-copy {
  min-width: 0;
}

.wizard-progress strong,
.wizard-progress small {
  display: block;
}

.wizard-progress strong {
  color: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25;
}

.wizard-progress li.active strong {
  color: var(--color-accent-soft);
}

.wizard-progress small {
  margin-top: 0.2rem;
  color: var(--color-text-mute);
  font-size: 0.72rem;
  line-height: 1.3;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.wizard-step-panel {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.footer-navigation {
  display: flex;
  gap: 0.75rem;
}

.creating-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 3rem 0;
}

.launch-state-icon {
  font-size: 2.5rem;
}

.launch-state-icon--loading {
  color: var(--primary);
}

.launch-state-icon--success {
  color: var(--success);
  font-size: 3rem;
}

.loader-text {
  font-size: 1.2rem;
  color: var(--primary);
  font-weight: 500;
}

.success-text {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--success);
}

@media (max-width: 768px) {
  .form-grid {
    max-height: 50vh;
  }

  .form-footer {
    flex-direction: column-reverse;
  }

  .form-footer button {
    width: 100%;
  }
}
</style>
