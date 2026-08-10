import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  toast: { add: vi.fn() },
  backendService: {
    createCampaign: vi.fn()
  }
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => mocks.toast
}))

vi.mock('@/services/backend', () => ({
  backendService: mocks.backendService
}))

import { useCampaignWizard } from '@/composables/useCampaignWizard'

function fillValidCampaign(wizard) {
  Object.assign(wizard.form.value, {
    name: '  Release campaign  ',
    description: 'Description',
    url: '  https://example.com/login?next=%2Fhome  ',
    public_domain: 'campaign.example.com',
    smtp_profile_id: 'smtp-1',
    email_template_id: 'template-1',
    landing_page_id: 'landing-1',
    plugin_ids: ['plugin-1'],
    module_ids: ['module-1'],
    target_list_id: 'targets-1',
    launch_type: 'scheduled',
    scheduled_date: '2030-08-01T10:00:00.000Z',
    scheduled_date_end: '2030-08-01T11:00:00.000Z',
    trackingParameter: 'source_id'
  })
}

describe('useCampaignWizard', () => {
  beforeEach(() => {
    mocks.backendService.createCampaign.mockResolvedValue({ id: 'campaign-1' })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it.each([
    ['empty URL', '', 'Enter a complete HTTP or HTTPS URL'],
    ['non-HTTP scheme', 'file:///etc/passwd', 'Only HTTP and HTTPS URLs are allowed'],
    ['command substitution', 'https://example.com/$(whoami)', 'Shell substitution sequences are not allowed in the target URL'],
    ['template substitution', 'https://example.com/${USER}', 'Shell substitution sequences are not allowed in the target URL'],
    ['backticks', 'https://example.com/`whoami`', 'Shell substitution sequences are not allowed in the target URL'],
    ['control characters', 'https://example.com/\nadmin', 'The URL contains control characters']
  ])('rejects %s', (_label, value, expectedError) => {
    const wizard = useCampaignWizard(vi.fn())
    wizard.form.value.url = value

    expect(wizard.isValidSourceUrl.value).toBe(false)
    expect(wizard.sourceUrlError.value).toBe(expectedError)
  })

  it('accepts a complete HTTPS URL with ordinary query metacharacters', () => {
    const wizard = useCampaignWizard(vi.fn())
    wizard.form.value.url = 'https://example.com/search?a=1&b=x|y;c=z'

    expect(wizard.isValidSourceUrl.value).toBe(true)
    expect(wizard.sourceUrlError.value).toBe('')
  })

  it('builds the expected campaign payload and emits completion', async () => {
    vi.useFakeTimers()
    const emit = vi.fn()
    const wizard = useCampaignWizard(emit)
    fillValidCampaign(wizard)

    await wizard.createCampaign()

    expect(mocks.backendService.createCampaign).toHaveBeenCalledOnce()
    expect(mocks.backendService.createCampaign).toHaveBeenCalledWith({
      name: 'Release campaign',
      description: 'Description',
      url: 'https://example.com/login?next=%2Fhome',
      public_domain: 'campaign.example.com',
      campaign_type: 'full',
      smtp_profile_id: 'smtp-1',
      email_template_id: 'template-1',
      landing_page_id: 'landing-1',
      plugin_ids: ['plugin-1'],
      module_ids: ['module-1'],
      target_list_id: 'targets-1',
      launch_type: 'scheduled',
      scheduled_date: '2030-08-01T10:00:00.000Z',
      scheduled_date_end: '2030-08-01T11:00:00.000Z',
      advanced_options: {
        protocol: 'selkies',
        tracking_parameter: 'source_id',
        selkies: {
          use_streaming_mode: true,
          use_paint_over_quality: true,
          video_quality: 'medium',
          framerate: 'medium',
          compression_level: 'medium'
        }
      }
    })
    expect(wizard.created.value).toBe(true)

    vi.advanceTimersByTime(1500)
    expect(emit).toHaveBeenCalledWith('campaign-created')
  })

  it('serializes DatePicker values as timezone-aware ISO timestamps', async () => {
    const wizard = useCampaignWizard(vi.fn())
    fillValidCampaign(wizard)
    wizard.form.value.scheduled_date = new Date('2030-08-01T10:00:00.000Z')
    wizard.form.value.scheduled_date_end = new Date('2030-08-01T11:00:00.000Z')

    await wizard.createCampaign()

    expect(mocks.backendService.createCampaign).toHaveBeenCalledWith(
      expect.objectContaining({
        scheduled_date: '2030-08-01T10:00:00.000Z',
        scheduled_date_end: '2030-08-01T11:00:00.000Z'
      })
    )
  })

  it('normalizes standalone campaigns and omits email scheduling', async () => {
    const wizard = useCampaignWizard(vi.fn())
    fillValidCampaign(wizard)

    wizard.form.value.campaign_type = 'standalone'
    await nextTick()

    expect(wizard.form.value.smtp_profile_id).toBeNull()
    expect(wizard.form.value.email_template_id).toBeNull()
    expect(wizard.form.value.launch_type).toBe('immediate')

    await wizard.createCampaign()

    expect(mocks.backendService.createCampaign).toHaveBeenCalledWith(
      expect.objectContaining({
        campaign_type: 'standalone',
        smtp_profile_id: null,
        email_template_id: null,
        launch_type: 'immediate',
        scheduled_date: null,
        scheduled_date_end: null
      })
    )
  })

  it('restores required scheduling when switching back to a complete campaign', async () => {
    const wizard = useCampaignWizard(vi.fn())

    wizard.form.value.campaign_type = 'standalone'
    await nextTick()
    expect(wizard.form.value.launch_type).toBe('immediate')

    wizard.form.value.campaign_type = 'full'
    await nextTick()

    expect(wizard.form.value.launch_type).toBe('scheduled')
    expect(wizard.hasValidSchedule.value).toBe(false)
  })

  it('returns to the invalid step instead of calling the backend', async () => {
    const wizard = useCampaignWizard(vi.fn())
    fillValidCampaign(wizard)
    wizard.form.value.url = 'javascript:alert(1)'
    wizard.currentStep.value = 3

    await wizard.createCampaign()

    expect(wizard.currentStep.value).toBe(2)
    expect(mocks.backendService.createCampaign).not.toHaveBeenCalled()
    expect(mocks.toast.add).toHaveBeenCalledWith(
      expect.objectContaining({ summary: 'Validation Error' })
    )
  })
})
