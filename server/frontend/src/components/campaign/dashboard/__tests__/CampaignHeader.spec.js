import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CampaignHeader from '@/components/campaign/dashboard/CampaignHeader.vue'

const completedCampaign = {
  name: 'Completed campaign',
  status: 'completed',
  campaign_type: 'email',
  from_email: 'sender@example.test',
  created_at: '2026-08-01T10:00:00Z',
  completed_at: '2026-08-01T11:00:00Z',
  scheduled_start: '2026-08-01T10:05:00Z',
  scheduled_end: '2026-08-01T12:00:00Z'
}

function mountHeader(campaign = completedCampaign) {
  return mount(CampaignHeader, {
    props: { campaign },
    global: {
      stubs: {
        Button: { template: '<button><slot /></button>' },
        Tag: { template: '<span />' }
      }
    }
  })
}

describe('CampaignHeader', () => {
  it('shows the actual end after Created and before Email delivery window', () => {
    const text = mountHeader().text()

    expect(text.indexOf('Created')).toBeLessThan(text.indexOf('Actually ended'))
    expect(text.indexOf('Actually ended')).toBeLessThan(text.indexOf('Email delivery window'))
  })

  it('does not show Actually ended for a campaign that is not completed', () => {
    const wrapper = mountHeader({ ...completedCampaign, status: 'active' })
    expect(wrapper.text()).not.toContain('Actually ended')
  })
})
