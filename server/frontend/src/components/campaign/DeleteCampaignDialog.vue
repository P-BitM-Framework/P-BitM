<script setup>
import { computed } from 'vue'
import ConfirmActionDialog from '@/components/default/ConfirmActionDialog.vue'

const props = defineProps({
  visible: Boolean,
  campaignName: String,
  deleting: Boolean
})

defineEmits(['cancel', 'confirm', 'update:visible'])

const message = computed(() =>
  props.campaignName
    ? `Delete “${props.campaignName}”?`
    : 'Delete this campaign?'
)
</script>

<template>
  <ConfirmActionDialog
    :visible="visible"
    title="Delete Campaign"
    :message="message"
    description="The campaign and its related resources will be permanently removed."
    confirm-label="Delete Campaign"
    confirm-icon="pi pi-trash"
    :busy="deleting"
    @update:visible="$emit('update:visible', $event)"
    @cancel="$emit('cancel')"
    @confirm="$emit('confirm')"
  />
</template>
