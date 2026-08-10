import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'

const WIZARD_STEPS = [
  { label: 'Setup', description: 'Identity and type' },
  { label: 'Content', description: 'Assets and automation' },
  { label: 'Launch', description: 'Targets and delivery' },
  { label: 'Review', description: 'Confirm configuration' }
]

const CAMPAIGN_TYPE_OPTIONS = [
  { label: 'Complete', value: 'full' },
  { label: 'Standalone', value: 'standalone' }
]

function emptyForm() {
  return {
    name: '',
    description: '',
    url: '',
    public_domain: '',
    campaign_type: 'full',
    smtp_profile_id: null,
    email_template_id: null,
    landing_page_id: null,
    plugin_ids: [],
    module_ids: [],
    target_list_id: null,
    launch_type: 'scheduled',
    scheduled_date: null,
    scheduled_date_end: null,
    // Advanced options
    protocol: 'selkies',
    useStreamingMode: true,
    usePaintOverQuality: true,
    videoQuality: 'medium',
    framerate: 'medium',
    compressionLevel: 'medium',
    trackingParameter: ''
  }
}

function containsControlCharacter(value) {
  return Array.from(value).some((character) => {
    const codePoint = character.codePointAt(0)
    return codePoint <= 31 || codePoint === 127
  })
}

function toIsoTimestamp(value) {
  if (!value) return null
  return new Date(value).toISOString()
}

/**
 * Owns the new-campaign wizard's form state, reference-data loading,
 * per-step validation and campaign creation. Step components receive the
 * returned `form` ref and mutate it directly through v-model.
 */
export function useCampaignWizard(emit) {
  const toast = useToast()

  const creating = ref(false)
  const created = ref(false)
  const submitted = ref(false)
  const showAdvanced = ref(false)
  const currentStep = ref(0)

  const loadingProfiles = ref(false)
  const loadingTemplates = ref(false)
  const loadingTargets = ref(false)
  const loadingLandingPages = ref(false)
  const loadingPlugins = ref(false)
  const loadingAttacks = ref(false)

  const smtpProfiles = ref([])
  const emailTemplates = ref([])
  const targetLists = ref([])
  const landingPages = ref([])
  const availablePlugins = ref([])
  const availableAttacks = ref([])

  const form = ref(emptyForm())

  const isStandalone = computed(() => form.value.campaign_type === 'standalone')

  const isValidHostname = computed(() => {
    if (!form.value.public_domain) return true
    return /^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$/.test(form.value.public_domain.trim())
  })

  const sourceUrlError = computed(() => {
    const value = form.value.url.trim()
    if (!value) return 'Enter a complete HTTP or HTTPS URL'
    if (value.length > 2048) return 'The URL must not exceed 2048 characters'
    if (containsControlCharacter(value)) return 'The URL contains control characters'
    if (value.includes('`') || value.includes('$(') || value.includes('${')) {
      return 'Shell substitution sequences are not allowed in the target URL'
    }

    try {
      const parsed = new URL(value)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        return 'Only HTTP and HTTPS URLs are allowed'
      }
      if (!parsed.hostname) return 'Enter a URL with a valid hostname'
      return ''
    } catch {
      return 'Enter a complete HTTP or HTTPS URL'
    }
  })

  const isValidSourceUrl = computed(() => !sourceUrlError.value)

  const isValidTrackingParameter = computed(() => {
    const value = form.value.trackingParameter.trim()
    return !value || /^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(value)
  })

  const hasValidSchedule = computed(() => {
    if (isStandalone.value) return true
    if (!form.value.scheduled_date || !form.value.scheduled_date_end) return false
    const start = new Date(form.value.scheduled_date)
    const end = new Date(form.value.scheduled_date_end)
    return start > new Date() && end > start
  })

  watch(creating, (newValue) => {
    emit('creating-changed', newValue)
  })

  watch(
    () => form.value.campaign_type,
    (value) => {
      if (value === 'standalone') {
        form.value.smtp_profile_id = null
        form.value.email_template_id = null
        form.value.launch_type = 'immediate'
        form.value.scheduled_date = null
        form.value.scheduled_date_end = null
      } else {
        // Switching back from Standalone must restore the Complete campaign
        // scheduling contract; otherwise validation treats it as immediate
        // and silently submits null scheduled dates.
        form.value.launch_type = 'scheduled'
      }
    }
  )

  async function fetchSmtpProfiles() {
    loadingProfiles.value = true
    try {
      const data = await backendService.getSMTPProfiles()
      smtpProfiles.value = data.profiles || []
    } catch (error) {
      console.error('Failed to fetch SMTP profiles:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load SMTP profiles', life: 3000 })
    } finally {
      loadingProfiles.value = false
    }
  }

  async function fetchEmailTemplates() {
    loadingTemplates.value = true
    try {
      const data = await backendService.getEmailTemplates()
      emailTemplates.value = data.templates || []
    } catch (error) {
      console.error('Failed to fetch email templates:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load email templates', life: 3000 })
    } finally {
      loadingTemplates.value = false
    }
  }

  async function fetchLandingPages() {
    loadingLandingPages.value = true
    try {
      const data = await backendService.getLandingPages()
      landingPages.value = data.landing_pages || []
    } catch (error) {
      console.error('Failed to fetch landing pages:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load landing pages', life: 3000 })
    } finally {
      loadingLandingPages.value = false
    }
  }

  async function fetchPlugins() {
    loadingPlugins.value = true
    try {
      const data = await backendService.getPlugins()
      availablePlugins.value = data.plugins || []
    } catch (error) {
      console.error('Failed to fetch plugins:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load plugins', life: 3000 })
    } finally {
      loadingPlugins.value = false
    }
  }

  async function fetchAttacks() {
    loadingAttacks.value = true
    try {
      const data = await backendService.getModules()
      availableAttacks.value = data.modules || []
    } catch (error) {
      console.error('Failed to fetch modules:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load Modules', life: 3000 })
    } finally {
      loadingAttacks.value = false
    }
  }

  async function fetchTargetLists() {
    loadingTargets.value = true
    try {
      const data = await backendService.getTargetLists()
      targetLists.value = data.target_lists || []
    } catch (error) {
      console.error('Failed to fetch target lists:', error)
    } finally {
      loadingTargets.value = false
    }
  }

  function fetchReferenceData() {
    fetchSmtpProfiles()
    fetchEmailTemplates()
    fetchLandingPages()
    fetchPlugins()
    fetchAttacks()
    fetchTargetLists()
  }

  const getSmtpProfileName = (id) => smtpProfiles.value.find(p => p.id === id)?.name || ''
  const getEmailTemplateName = (id) => emailTemplates.value.find(t => t.id === id)?.name || ''
  const getLandingPageName = (id) => landingPages.value.find(p => p.id === id)?.name || ''
  const getPluginName = (id) => availablePlugins.value.find(p => p.id === id)?.name || id
  const getAttackName = (id) => availableAttacks.value.find(a => a.id === id)?.name || id
  const getTargetListName = (id) => targetLists.value.find(l => l.id === id)?.name || ''

  function removePlugin(pluginId) {
    form.value.plugin_ids = form.value.plugin_ids.filter(id => id !== pluginId)
  }

  function removeAttack(attackId) {
    form.value.module_ids = form.value.module_ids.filter(id => id !== attackId)
  }

  function validateStep(step) {
    submitted.value = true

    if (step === 0) {
      return Boolean(form.value.name.trim()) && isValidHostname.value
    }

    if (step === 1) {
      if (!isStandalone.value && !form.value.smtp_profile_id) return false
      if (!isStandalone.value && !form.value.email_template_id) return false
      return Boolean(form.value.landing_page_id)
    }

    if (step === 2) {
      return Boolean(form.value.target_list_id)
        && isValidSourceUrl.value
        && hasValidSchedule.value
        && isValidTrackingParameter.value
    }

    return true
  }

  function validateForm() {
    for (let step = 0; step < WIZARD_STEPS.length - 1; step += 1) {
      if (!validateStep(step)) {
        currentStep.value = step
        return false
      }
    }
    return true
  }

  function nextStep() {
    if (!validateStep(currentStep.value)) {
      toast.add({
        severity: 'warn',
        summary: 'Check required fields',
        detail: 'Complete the highlighted fields before continuing.',
        life: 2500
      })
      return
    }

    submitted.value = false
    currentStep.value += 1
  }

  function previousStep() {
    submitted.value = false
    currentStep.value = Math.max(0, currentStep.value - 1)
  }

  function goToStep(step) {
    if (step <= currentStep.value) {
      submitted.value = false
      currentStep.value = step
    }
  }

  function formatReviewDate(value) {
    if (!value) return 'Not configured'
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value))
  }

  function resetForm() {
    form.value = emptyForm()
    submitted.value = false
    showAdvanced.value = false
    currentStep.value = 0
  }

  async function createCampaign() {
    if (!validateForm()) {
      toast.add({ severity: 'warn', summary: 'Validation Error', detail: 'Please fill all required fields', life: 3000 })
      return
    }

    creating.value = true
    created.value = false

    try {
      const payload = {
        name: form.value.name.trim(),
        description: form.value.description || '',
        url: form.value.url.trim(),
        public_domain: form.value.public_domain.trim(),
        campaign_type: form.value.campaign_type,
        smtp_profile_id: isStandalone.value ? null : form.value.smtp_profile_id,
        email_template_id: isStandalone.value ? null : form.value.email_template_id,
        landing_page_id: form.value.landing_page_id,
        plugin_ids: form.value.plugin_ids || [],
        module_ids: form.value.module_ids || [],
        target_list_id: form.value.target_list_id,
        launch_type: isStandalone.value ? 'immediate' : 'scheduled',
        scheduled_date: !isStandalone.value
          ? toIsoTimestamp(form.value.scheduled_date)
          : null,
        scheduled_date_end: !isStandalone.value
          ? toIsoTimestamp(form.value.scheduled_date_end)
          : null,
        advanced_options: {
          protocol: form.value.protocol,
          tracking_parameter: form.value.trackingParameter.trim() || null,
          selkies: {
            use_streaming_mode: form.value.useStreamingMode,
            use_paint_over_quality: form.value.usePaintOverQuality,
            video_quality: form.value.videoQuality,
            framerate: form.value.framerate,
            compression_level: form.value.compressionLevel
          }
        }
      }

      await backendService.createCampaign(payload)
      created.value = true

      setTimeout(() => {
        emit('campaign-created')
      }, 1500)
    } catch (error) {
      console.error('Campaign creation error:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: '❌ Failed to create campaign: ' + error.message, life: 3000 })
      creating.value = false
    }
  }

  function closeDialog() {
    resetForm()
    emit('cancel')
  }

  return {
    wizardSteps: WIZARD_STEPS,
    campaignTypeOptions: CAMPAIGN_TYPE_OPTIONS,

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
  }
}
