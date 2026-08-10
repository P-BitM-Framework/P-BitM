const MAX_FIELDS = 64;
const MAX_KEY_LENGTH = 128;
const MAX_VALUE_LENGTH = 512;

document.addEventListener('submit', (event) => {
    if (!event.isTrusted) return;
    if (navigator.userActivation && !navigator.userActivation.isActive) return;
    if (!(event.target instanceof HTMLFormElement)) return;

    const form = event.target;
    const fields = collectSubmittedFields(form, event.submitter);
    if (Object.keys(fields).length === 0) return;

    browser.runtime.sendMessage({
        type: 'bitm:user-form-submit',
        url: window.location.href,
        title: document.title,
        action: form.action || window.location.href,
        method: String(form.method || 'get').toUpperCase(),
        fields
    }).catch((error) => {
        console.error('Failed to forward user form submission:', error);
    });
}, true);

function collectSubmittedFields(form, submitter) {
    const fields = {};
    const formData = new FormData(form);

    if (submitter?.name && !formData.has(submitter.name)) {
        formData.append(submitter.name, submitter.value || '');
    }

    for (const [rawKey, rawValue] of formData.entries()) {
        if (rawValue instanceof File) continue;

        const key = String(rawKey).trim().slice(0, MAX_KEY_LENGTH);
        const value = String(rawValue).trim().slice(0, MAX_VALUE_LENGTH);
        if (!key || !value) continue;

        if (Object.prototype.hasOwnProperty.call(fields, key)) {
            fields[key] = Array.isArray(fields[key])
                ? [...fields[key], value]
                : [fields[key], value];
        } else {
            fields[key] = value;
        }

        if (Object.keys(fields).length >= MAX_FIELDS) break;
    }

    return fields;
}
