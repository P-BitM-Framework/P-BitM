// admin-frontend/src/main.js

import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config'
import { BitmPreset } from '@/theme/preset'
import { initializeTheme } from '@/composables/useTheme'

// Import each PrimeVue component from its own subpath (not the 'primevue'
// barrel export) so Rollup only bundles the components actually used here,
// instead of pulling the whole library into the eagerly-loaded main chunk.
//
// Heavy, narrowly-used components (DataTable, Column, DatePicker,
// MultiSelect, Select, InputNumber, ContextMenu, FileUpload, Password) are
// deliberately NOT registered globally here: they account for the majority
// of PrimeVue's footprint and are only needed by specific, already
// lazy-loaded routes. Those views import and use them locally instead, so
// they land in the route's own chunk rather than in every page load.
import ToggleSwitch from 'primevue/toggleswitch'
import Chip from 'primevue/chip'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Toast from 'primevue/toast'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Breadcrumb from 'primevue/breadcrumb'
import Tabs from 'primevue/tabs'
import Tab from 'primevue/tab'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import TabList from 'primevue/tablist'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Textarea from 'primevue/textarea'
import ProgressSpinner from 'primevue/progressspinner'

import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import { createPinia } from 'pinia'
import router from './router'

window.addEventListener('pointerdown', () => {
  document.documentElement.dataset.inputModality = 'pointer'
}, { capture: true, passive: true })

window.addEventListener('keydown', () => {
  document.documentElement.dataset.inputModality = 'keyboard'
}, { capture: true })

initializeTheme()

const app = createApp(App)

// Pinia store
app.use(createPinia())

// Toast service
app.use(ToastService)

// PrimeVue config
app.use(PrimeVue, {
  theme: {
    preset: BitmPreset,
    options: {
      darkModeSelector: '.dark-mode',
      cssLayer: {
        name: 'primevue',
        order: 'tailwind-base, primevue, tailwind-utilities'
      }
    }
  }
})

// Router
app.use(router)

// ========================================
// GLOBAL COMPONENTS
// ========================================

// Existing components
app.component('ToggleSwitch', ToggleSwitch)
app.component('Card', Card)
app.component('Button', Button)
app.component('InputText', InputText)
app.component('Toast', Toast)
app.component('Dialog', Dialog)
app.component('Message', Message)
app.component('Checkbox', Checkbox)
app.component('Divider', Divider)
app.component('SelectButton', SelectButton)
app.component('Tag', Tag)
app.component('Breadcrumb', Breadcrumb)
app.component('Tabs', Tabs)
app.component('Tab', Tab)
app.component('TabPanel', TabPanel)
app.component('TabPanels', TabPanels)
app.component('TabList', TabList)

// ✅ New components for views
app.component('IconField', IconField)
app.component('InputIcon', InputIcon)
app.component('Textarea', Textarea)
app.component('ProgressSpinner', ProgressSpinner)
app.component('Chip', Chip)

// ========================================
// GLOBAL DIRECTIVES
// ========================================
app.directive('tooltip', Tooltip)

// Mount app
app.mount('#app')
