import { createTargetListsClient } from './targetLists'
import { createEmailTemplatesClient } from './emailTemplates'
import { createSendingProfilesClient } from './sendingProfiles'
import { createLandingPagesClient } from './landingPages'
import { createModulesClient } from './modules'
import { createPluginsClient } from './plugins'

/**
 * Combined client for the reusable campaign assets: target lists, email
 * templates, sending profiles, landing pages, modules and plugins.
 */
export function createLibraryClient(apiClient) {
  return {
    ...createTargetListsClient(apiClient),
    ...createEmailTemplatesClient(apiClient),
    ...createSendingProfilesClient(apiClient),
    ...createLandingPagesClient(apiClient),
    ...createModulesClient(apiClient),
    ...createPluginsClient(apiClient)
  }
}
