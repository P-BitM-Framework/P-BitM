<template>
  <div class="sending-profiles-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader title="SMTP Profiles" subtitle="Configure SMTP servers for email campaigns">
      <template #actions>
        <Button label="New SMTP Profile" icon="pi pi-plus" @click="openCreateDialog" />
      </template>
    </PageHeader>

    <!-- Stats Cards -->
    <div class="stats-row metrics-grid">
      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-server"></i>
            <div class="stat-text">
              <div class="stat-value">{{ profiles.length }}</div>
              <div class="stat-label">Total Profiles</div>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-check-circle"></i>
            <div class="stat-text">
              <div class="stat-value">{{ activeProfiles }}</div>
              <div class="stat-label">Active</div>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-send"></i>
            <div class="stat-text">
              <div class="stat-value">{{ usedInCampaigns }}</div>
              <div class="stat-label">Used in Campaigns</div>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-exclamation-triangle"></i>
            <div class="stat-text">
              <div class="stat-value">{{ failedProfiles }}</div>
              <div class="stat-label">Connection Issues</div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Table Card -->
    <Card class="profiles-table-card app-table-card">
      <template #content>
        <!-- Table Header -->
        <div class="table-header app-table-header">
          <h2 class="section-title app-section-title">
            <i class="pi pi-server"></i>
            SMTP Profiles
            <span class="count-badge">{{ profiles.length }}</span>
          </h2>

          <div class="table-controls app-table-controls">
            <IconField iconPosition="left">
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText
                v-model="filters['global'].value"
                placeholder="Search profiles..."
                class="search-input"
              />
            </IconField>

            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              @click="fetchSMTPProfiles"
              :loading="showLoading"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <!-- DataTable -->
        <DataTable
          :value="profiles"
          :loading="showLoading"
          :filters="filters"
          clickableRows
          @row-click="openEditDialog($event.data)"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          class="data-table data-table--interactive"
        >
          <Column field="name" header="Profile Name" sortable style="min-width: 200px">
            <template #body="{ data }">
              <div class="profile-cell">
                <div class="profile-icon">
                  <i class="pi pi-server"></i>
                </div>
                <strong>{{ data.name }}</strong>
              </div>
            </template>
          </Column>

          <Column field="smtp_host" header="SMTP Host" sortable></Column>

          <Column field="smtp_port" header="Port" sortable style="width: 100px"></Column>

          <Column field="from_email" header="From Email" sortable></Column>

          <Column header="Status" style="width: 130px">
            <template #body="{ data }">
              <Tag
                :value="getStatusLabel(data.is_active)"
                :severity="getStatusSeverity(data.is_active)"
                :icon="getStatusIcon(data.is_active)"
              />
            </template>
          </Column>

          <Column field="campaigns_count" header="Campaigns" sortable style="width: 120px">
            <template #body="{ data }">
              <div class="usage-badge">
                <i class="pi pi-send"></i>
                {{ data.campaigns_count || 0 }}
              </div>
            </template>
          </Column>

          <Column header="Actions" style="width: 150px" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-play"
                  severity="success"
                  text
                  rounded
                  v-tooltip.top="'Test Connection'"
                  @click.stop="testSMTPProfile(data)"
                />
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Edit'"
                  @click.stop="openEditDialog(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  v-tooltip.top="'Delete'"
                  @click.stop="confirmDeleteSMTPProfile(data)"
                />
              </div>
            </template>
          </Column>

          <template #empty>
            <div class="empty-state">
              <i class="pi pi-server"></i>
              <p>No sending profiles found. Create your first SMTP profile.</p>
              <Button
                label="Create Profile"
                icon="pi pi-plus"
                @click="openCreateDialog"
                size="small"
                class="mt-2"
              />
            </div>
          </template>
        </DataTable>
      </template>
    </Card>
    </DelayedContent>

    <!-- Create/Edit Sending Profile Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      modal
      :header="dialogMode === 'edit' ? 'Edit Sending Profile' : 'Create Sending Profile'"
      :style="{ width: '700px' }"
      :draggable="false"
      @hide="onDialogHide"
    >
      <div class="form-grid">
        <!-- Profile Name -->
        <div class="field">
          <label for="profileName">Profile Name <span class="required">*</span></label>
          <InputText
            id="profileName"
            v-model="profileForm.name"
            class="w-full"
            placeholder="My SMTP Server"
            :invalid="submitted && !profileForm.name"
          />
          <small v-if="submitted && !profileForm.name" class="p-error">Name is required</small>
        </div>

        <!-- SMTP Host & Port -->
        <div class="field-row">
          <div class="field">
            <label for="smtpHost">SMTP Host <span class="required">*</span></label>
            <InputText
              id="smtpHost"
              v-model="profileForm.smtp_host"
              class="w-full"
              placeholder="smtp.gmail.com"
              :invalid="submitted && !profileForm.smtp_host"
            />
            <small v-if="submitted && !profileForm.smtp_host" class="p-error">Host is required</small>
          </div>

          <div class="field">
            <label for="smtpPort">Port <span class="required">*</span></label>
            <InputNumber
              id="smtpPort"
              v-model="profileForm.smtp_port"
              class="w-full"
              placeholder="587"
              :invalid="submitted && !profileForm.smtp_port"
              :useGrouping="false"
            />
            <small v-if="submitted && !profileForm.smtp_port" class="p-error">Port is required</small>
          </div>
        </div>

        <!-- Username & Password -->
        <div class="field-row">
          <div class="field">
            <label for="username">Username</label>
            <InputText
              id="username"
              v-model="profileForm.smtp_username"
              class="w-full"
              placeholder="user@example.com"
            />
          </div>

          <div class="field">
            <label for="password">Password</label>
            <Password
              id="password"
              v-model="profileForm.smtp_password"
              class="w-full"
              placeholder="••••••••"
              :feedback="false"
              toggleMask
            />
          </div>
        </div>

        <!-- From Email & From Name -->
        <div class="field-row">
          <div class="field">
            <label for="fromEmail">From Email <span class="required">*</span></label>
            <InputText
              id="fromEmail"
              v-model="profileForm.from_email"
              class="w-full"
              placeholder="noreply@example.com"
              :invalid="submitted && !profileForm.from_email"
            />
            <small v-if="submitted && !profileForm.from_email" class="p-error">From email is required</small>
          </div>

          <div class="field">
            <label for="fromName">From Name</label>
            <InputText
              id="fromName"
              v-model="profileForm.from_name"
              class="w-full"
              placeholder="Company Name"
            />
          </div>
        </div>

        <!-- Security Options -->
        <div class="field-row">
          <div class="field">
            <label for="encryption">Encryption</label>
            <Select
              id="encryption"
              v-model="profileForm.encryption"
              :options="encryptionOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Select encryption"
              class="w-full"
            />
          </div>

          <div class="field">
            <label>&nbsp;</label>
            <div
              class="certificate-option"
              :class="{ 'is-disabled': !usesEncryptedTransport }"
              :aria-disabled="!usesEncryptedTransport"
              :title="!usesEncryptedTransport ? 'Enable SSL, TLS, or STARTTLS to use this option' : undefined"
            >
              <Checkbox
                v-model="profileForm.ignore_cert_errors"
                inputId="ignoreCert"
                :binary="true"
                :disabled="!usesEncryptedTransport"
              />
              <label
                for="ignoreCert"
                class="mb-0"
              >
                Ignore certificate errors
              </label>
            </div>
            <small
              v-if="usesEncryptedTransport"
              class="security-warning"
            >
              Disables certificate authority and hostname verification. Use only
              for trusted SMTP servers with self-signed certificates.
            </small>
            <small v-else class="field-hint">
              Available only when SSL or TLS is enabled.
            </small>
          </div>
        </div>

        <!-- Test Connection Toggle (solo in create mode) -->
        <div class="field" v-if="dialogMode === 'create'">
          <div class="flex align-items-center">
            <Checkbox
              v-model="testAfterCreate"
              inputId="testAfterCreate"
              :binary="true"
            />
            <label for="testAfterCreate" class="ml-2 mb-0">Test connection after creating</label>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showCreateDialog = false" />
        <Button
          :label="dialogMode === 'edit' ? 'Update Profile' : 'Create Profile'"
          :loading="saving"
          @click="saveSMTPProfile"
        />
      </template>
    </Dialog>

    <!-- Test Connection Dialog -->
    <Dialog
      v-model:visible="showTestDialog"
      modal
      header="Test SMTP Connection"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="test-content">
        <div v-if="testing" class="testing-state">
          <ProgressSpinner style="width: 50px; height: 50px" />
          <p>Testing connection to {{ profileToTest?.smtp_host }}...</p>
        </div>

        <div v-else-if="testResult" class="test-result">
          <div v-if="testResult.success" class="success-result">
            <div class="result-icon success">
              <i class="pi pi-check-circle"></i>
            </div>
            <h3>Connection Successful</h3>
            <p>{{ testResult.message }}</p>
          </div>

          <div v-else class="error-result">
            <div class="result-icon error">
              <i class="pi pi-times-circle"></i>
            </div>
            <h3>Connection Failed</h3>
            <p>{{ testResult.message }}</p>
            <Message severity="error" v-if="testResult.details" class="mt-3">
              {{ testResult.details }}
            </Message>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Close" severity="secondary" text @click="showTestDialog = false" />
        <Button
          v-if="testResult && !testResult.success"
          label="Retry"
          icon="pi pi-refresh"
          @click="testSMTPProfile(profileToTest)"
        />
      </template>
    </Dialog>

    <DeleteResourceDialog
      v-model:visible="showDeleteDialog"
      header="Delete Sending Profile"
      :subject="profileToDelete?.name"
      confirm-label="Delete Profile"
      :loading="deleting"
      @confirm="deleteSMTPProfile"
    >
      <p>
        This profile has been used in
        <strong>{{ profileToDelete?.campaigns_count || 0 }} campaigns</strong>.
      </p>
      <Message severity="warn" :closable="false" class="mt-3">
        This action cannot be undone
      </Message>
    </DeleteResourceDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import { backendService } from '@/services/backend'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'
import DeleteResourceDialog from '@/components/default/DeleteResourceDialog.vue'

const toast = useToast()

// State
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const testing = ref(false)
const deleting = ref(false)
const submitted = ref(false)
const testAfterCreate = ref(true)

const profiles = ref([])
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const showDeleteDialog = ref(false)
const dialogMode = ref('create') // 'create' or 'edit'
const profileToTest = ref(null)
const profileToDelete = ref(null)
const testResult = ref(null)

const profileForm = ref({
  name: '',
  host: '',
  port: 587,
  username: '',
  password: '',
  from_email: '',
  from_name: '',
  encryption: 'tls',
  ignore_cert_errors: false
})

const encryptionOptions = [
  { label: 'None', value: 'none' },
  { label: 'SSL', value: 'ssl' },
  { label: 'TLS', value: 'tls' },
  { label: 'STARTTLS', value: 'starttls' }
]

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const activeProfiles = computed(() => {
  return profiles.value.filter(p => p.campaigns_count > 0).length
})

const usedInCampaigns = computed(() => {
  return profiles.value.filter(p => p.campaigns_count > 0).length
})

const failedProfiles = computed(() => {
  return profiles.value.filter(p => p.is_active === 'failed').length
})

const usesEncryptedTransport = computed(() => {
  return profileForm.value.encryption !== 'none'
})

watch(
  () => profileForm.value.encryption,
  (encryption) => {
    if (encryption === 'none') {
      profileForm.value.ignore_cert_errors = false
    }
  }
)

// Methods
const fetchSMTPProfiles = async () => {
  loading.value = true
  try {
    const data = await backendService.getSMTPProfiles()
    profiles.value = data.profiles || []

  } catch (error) {
    console.error('Failed to fetch sending profiles:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load sending profiles',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  profileForm.value = {
    name: '',
    smtp_host: '',
    smtp_port: '',
    smtp_username: '',
    smtp_password: '',
    from_email: '',
    from_name: '',
    encryption: 'tls',
    ignore_cert_errors: false
  }
  testAfterCreate.value = true
  submitted.value = false
  showCreateDialog.value = true
}

const openEditDialog = (profile) => {
  dialogMode.value = 'edit'
  profileForm.value = {
    ...profile,
    smtp_password: '',
    encryption: profile.smtp_use_ssl
      ? 'ssl'
      : profile.smtp_use_tls
        ? 'tls'
        : 'none'
  }
  submitted.value = false
  showCreateDialog.value = true
}

const saveSMTPProfile = async () => {
  submitted.value = true
  const saveMode = dialogMode.value

  // Validation
  if (!profileForm.value.name || !profileForm.value.smtp_host || !profileForm.value.smtp_port || !profileForm.value.from_email) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Please fill all required fields',
      life: 3000
    })
    return
  }

  saving.value = true
  try {
    let result
    if (saveMode === 'edit') {
      result = await backendService.updateSMTPProfile(profileForm.value.id, profileForm.value)
      toast.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Sending profile updated and connection verified',
        life: 3000
      })
    } else {
      result = await backendService.createSMTPProfile(profileForm.value)
      toast.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Sending profile created successfully',
        life: 3000
      })
    }

    showCreateDialog.value = false
    await fetchSMTPProfiles()

    // Test the connection if requested (create mode only).
    if (testAfterCreate.value && saveMode === 'create' && result?.id) {
      setTimeout(() => {
        testSMTPProfile(result)
      }, 500)
    }
  } catch (error) {
    console.error('Failed to save sending profile:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to save sending profile',
      life: 3000
    })
  } finally {
    saving.value = false
    submitted.value = false
  }
}

const testSMTPProfile = async (profile) => {
  profileToTest.value = profile
  showTestDialog.value = true
  testing.value = true
  testResult.value = null

  try {
    const result = await backendService.testSMTPProfile(profile.id)
    testResult.value = result

    if (result.success) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'SMTP connection successful',
        life: 3000
      })
      await fetchSMTPProfiles() // Refresh to update status
    } else {
      toast.add({
        severity: 'error',
        summary: 'Failed',
        detail: 'SMTP connection failed',
        life: 3000
      })
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    testResult.value = {
      success: false,
      message: 'Connection test failed',
      details: error.message
    }
  } finally {
    testing.value = false
  }
}

const confirmDeleteSMTPProfile = (profile) => {
  profileToDelete.value = profile
  showDeleteDialog.value = true
}

const deleteSMTPProfile = async () => {
  if (!profileToDelete.value) return

  deleting.value = true
  try {
    await backendService.deleteSMTPProfile(profileToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: `Profile "${profileToDelete.value.name}" deleted successfully`,
      life: 3000
    })
    showDeleteDialog.value = false
    profileToDelete.value = null
    await fetchSMTPProfiles()
  } catch (error) {
    console.error('Failed to delete profile:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete profile',
      life: 3000
    })
  } finally {
    deleting.value = false
  }
}

const onDialogHide = () => {
  // Reset the form once the dialog closes.
  profileForm.value = {
    name: '',
    host: '',
    port: '',
    username: '',
    password: '',
    from_email: '',
    from_name: '',
    encryption: 'tls',
    ignore_cert_errors: false
  }
  submitted.value = false
  testAfterCreate.value = true
  dialogMode.value = 'create'
}

const getStatusLabel = (status) => {
  const labels = {
    true: 'Active',
    false: 'Inactive',
    'failed': 'Failed',
    'testing': 'Testing'
  }
  return labels[status] || 'Unknown'
}

const getStatusSeverity = (status) => {
  const severities = {
    true: 'success',
    false: 'secondary',
    'failed': 'danger',
    'testing': 'warning'
  }
  return severities[status] || 'secondary'
}

const getStatusIcon = (status) => {
  const icons = {
    true: 'pi pi-check-circle',
    false: 'pi pi-circle',
    'failed': 'pi pi-times-circle',
    'testing': 'pi pi-spin pi-spinner'
  }
  return icons[status] || 'pi pi-circle'
}

onMounted(() => {
  fetchSMTPProfiles()
})
</script>

<style scoped src="../assets/views/smtp-profiles.css"></style>
