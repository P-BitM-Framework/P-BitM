<script setup>
import { computed } from 'vue'
import ConfirmActionDialog from '@/components/default/ConfirmActionDialog.vue'

const props = defineProps({
  visible: Boolean,
  campaignName: String,
  stopping: Boolean
})

defineEmits(['cancel', 'confirm', 'update:visible'])

const message = computed(() =>
  props.campaignName
    ? `Stop “${props.campaignName}”?`
    : 'Stop this campaign?'
)
</script>

<template>
  <ConfirmActionDialog
    :visible="visible"
    title="Stop Campaign"
    :message="message"
    description="Active delivery and campaign processing will stop. This action cannot be undone"
    confirm-label="Stop Campaign"
    confirm-icon="pi pi-stop"
    :busy="stopping"
    @update:visible="$emit('update:visible', $event)"
    @cancel="$emit('cancel')"
    @confirm="$emit('confirm')"
  />
</template>
