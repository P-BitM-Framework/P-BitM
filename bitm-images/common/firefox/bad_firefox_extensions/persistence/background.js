const LOGOUT_MESSAGE = "logoutIntercepted";
const LOGOUT_ROUTE = /(?:^|[\/_?&.=-])(?:(?:log|sign)[ _-]?(?:out|off)|(?:exit|disconnect|terminate)[ _-]?session)(?:$|[\/_?&.=-])/i;
const pendingLogoutActions = new Map();

function isLogoutRequest(rawUrl) {
    try {
        const url = new URL(rawUrl);
        const route = `${decodeURIComponent(url.pathname)}?${decodeURIComponent(url.search)}`;
        return LOGOUT_ROUTE.test(route);
    } catch (_error) {
        return false;
    }
}

function cookieUrl(cookie) {
    const domain = cookie.domain.replace(/^\./, "");
    return `${cookie.secure ? "https" : "http"}://${domain}${cookie.path || "/"}`;
}

async function clearCookieStore(cookieStoreId) {
    const query = { firstPartyDomain: null };
    if (cookieStoreId) query.storeId = cookieStoreId;

    const cookies = await browser.cookies.getAll(query);
    const results = await Promise.allSettled(cookies.map((cookie) => {
        const details = {
            url: cookieUrl(cookie),
            name: cookie.name,
            storeId: cookie.storeId
        };
        if (typeof cookie.firstPartyDomain === "string") {
            details.firstPartyDomain = cookie.firstPartyDomain;
        }
        if (cookie.partitionKey) details.partitionKey = cookie.partitionKey;
        return browser.cookies.remove(details);
    }));

    return {
        removed: results.filter(
            (result) => result.status === "fulfilled" && result.value
        ).length,
        failed: results.filter((result) => result.status === "rejected").length
    };
}

function logoutActionKey(cookieStoreId, tabId) {
    return `${cookieStoreId || "default"}:${Number.isInteger(tabId) ? tabId : "none"}`;
}

async function clearCookiesAndReload({ cookieStoreId, tabId, source, url }) {
    const key = logoutActionKey(cookieStoreId, tabId);
    if (pendingLogoutActions.has(key)) return pendingLogoutActions.get(key);

    const action = (async () => {
        const { removed, failed } = await clearCookieStore(cookieStoreId);
        let reloaded = false;
        if (Number.isInteger(tabId) && tabId >= 0) {
            await browser.tabs.reload(tabId);
            reloaded = true;
        }
        console.log(
            `[persistence] ${source}: cleared ${removed} cookies from the current ` +
            `cookie store${reloaded ? " and reloaded the tab" : ""}` +
            (failed ? ` (${failed} could not be cleared)` : "") +
            (url ? `: ${url}` : "")
        );
        return { removed, failed, reloaded };
    })();

    pendingLogoutActions.set(key, action);
    try {
        return await action;
    } finally {
        pendingLogoutActions.delete(key);
    }
}

function logCleanupFailure(error) {
    console.error("[persistence] Could not clear the current cookie store", error);
}

browser.runtime.onMessage.addListener((message, sender) => {
    if (!message || message.action !== LOGOUT_MESSAGE) return undefined;

    return clearCookiesAndReload({
        cookieStoreId: sender.tab && sender.tab.cookieStoreId,
        tabId: sender.tab && sender.tab.id,
        source: "Blocked logout control"
    });
});

function blockLogoutRequest(details) {
    if (!isLogoutRequest(details.url)) return undefined;

    clearCookiesAndReload({
        cookieStoreId: details.cookieStoreId,
        tabId: details.tabId,
        source: "Blocked logout request",
        url: details.url
    }).catch(logCleanupFailure);
    return { cancel: true };
}

browser.webRequest.onBeforeRequest.addListener(
    blockLogoutRequest,
    {
        urls: ["<all_urls>"],
        types: ["main_frame", "sub_frame", "xmlhttprequest"]
    },
    ["blocking"]
);

console.log("[persistence] Logout interceptor ready");
