import { describe, expect, it, vi } from 'vitest'

import { createEmailTemplatesClient } from '@/services/api/library/emailTemplates'
import { createLandingPagesClient } from '@/services/api/library/landingPages'
import { createModulesClient } from '@/services/api/library/modules'
import { createSendingProfilesClient } from '@/services/api/library/sendingProfiles'
import { createTargetListsClient } from '@/services/api/library/targetLists'

function mockApi() {
  const apiClient = {
    request: vi.fn().mockResolvedValue({ id: 'saved-id' })
  }
  return { apiClient, request: apiClient.request }
}

function requestBody(request) {
  return JSON.parse(request.mock.calls[0][1].body)
}

describe('library mutation payloads', () => {
  it('exposes email update and strips response/UI-only fields', async () => {
    const { apiClient, request } = mockApi()
    const client = createEmailTemplatesClient(apiClient)

    await client.updateEmailTemplate('template-1', {
      id: 'template-1',
      name: 'Updated',
      subject: 'Subject',
      html_content: '<p>Body</p>',
      content_type: 'html',
      usage_count: 4,
      created_at: 'yesterday',
      updated_at: 'today'
    })

    expect(request).toHaveBeenCalledWith('api/email-templates/template-1', {
      method: 'PUT',
      body: expect.any(String)
    })
    expect(requestBody(request)).toEqual({
      name: 'Updated',
      subject: 'Subject',
      html_content: '<p>Body</p>'
    })
  })

  it('encodes the email clone name as the backend query parameter', async () => {
    const { apiClient, request } = mockApi()
    const client = createEmailTemplatesClient(apiClient)

    await client.cloneEmailTemplate('template-1', { name: 'Copy & review' })

    expect(request).toHaveBeenCalledWith(
      'api/email-templates/template-1/duplicate?new_name=Copy%20%26%20review',
      { method: 'POST' }
    )
  })

  it('strips landing-page response metadata', async () => {
    const { apiClient, request } = mockApi()
    const client = createLandingPagesClient(apiClient)

    await client.updateLandingPage('page-1', {
      id: 'page-1',
      name: 'Portal',
      description: 'Updated',
      content: '<main>Ready</main>',
      created_at: 'yesterday',
      updated_at: 'today'
    })

    expect(requestBody(request)).toEqual({
      name: 'Portal',
      description: 'Updated',
      content: '<main>Ready</main>'
    })
  })

  it('strips module metadata and unsupported nested input fields', async () => {
    const { apiClient, request } = mockApi()
    const client = createModulesClient(apiClient)

    await client.updateModule('module-1', {
      id: 'module-1',
      name: 'Collector',
      category: 'Collection',
      payload: '<p>payload</p>',
      created_at: 'yesterday',
      updated_at: 'today',
      inputs: [{
        id: 0,
        label: 'Value',
        type: 'string',
        required: true,
        options: ['not-supported']
      }]
    })

    expect(requestBody(request)).toEqual({
      name: 'Collector',
      category: 'Collection',
      payload: '<p>payload</p>',
      inputs: [{
        id: 0,
        label: 'Value',
        type: 'string',
        required: true
      }]
    })
  })

  it('maps SMTP encryption and preserves an existing secret on update', async () => {
    const { apiClient, request } = mockApi()
    const client = createSendingProfilesClient(apiClient)

    await client.updateSMTPProfile('smtp-1', {
      id: 'smtp-1',
      name: 'Relay',
      smtp_host: 'smtp.example.test',
      smtp_port: 465,
      smtp_username: 'mailer',
      smtp_password: '',
      from_email: 'mailer@example.test',
      encryption: 'ssl',
      ignore_cert_errors: false,
      usage_count: 2,
      campaigns_count: 1,
      created_at: 'yesterday',
      updated_at: 'today',
      last_used_at: null
    })

    expect(requestBody(request)).toEqual({
      name: 'Relay',
      smtp_host: 'smtp.example.test',
      smtp_port: 465,
      smtp_username: 'mailer',
      from_email: 'mailer@example.test',
      smtp_use_tls: false,
      smtp_use_ssl: true,
      ignore_cert_errors: false
    })
  })

  it('clears certificate bypass when SMTP encryption is disabled', async () => {
    const { apiClient, request } = mockApi()
    const client = createSendingProfilesClient(apiClient)

    await client.updateSMTPProfile('smtp-1', {
      name: 'Plain relay',
      smtp_host: 'smtp.example.test',
      smtp_port: 25,
      smtp_username: '',
      smtp_password: '',
      from_email: 'mailer@example.test',
      encryption: 'none',
      ignore_cert_errors: true
    })

    expect(requestBody(request)).toMatchObject({
      smtp_use_tls: false,
      smtp_use_ssl: false,
      ignore_cert_errors: false
    })
  })

  it('exposes target listing/update and strips target response metadata', async () => {
    const { apiClient, request } = mockApi()
    const client = createTargetListsClient(apiClient)

    await client.getTargets('list-1')
    expect(request).toHaveBeenLastCalledWith('api/target-lists/list-1/targets')

    request.mockClear()
    await client.updateTarget('list-1', 'target-1', {
      id: 'target-1',
      target_list_id: 'list-1',
      email: 'person@example.test',
      first_name: 'Person',
      created_at: 'yesterday',
      updated_at: 'today'
    })

    expect(request).toHaveBeenCalledWith(
      'api/target-lists/list-1/targets/target-1',
      {
        method: 'PUT',
        body: expect.any(String)
      }
    )
    expect(requestBody(request)).toEqual({
      email: 'person@example.test',
      first_name: 'Person'
    })
  })
})
