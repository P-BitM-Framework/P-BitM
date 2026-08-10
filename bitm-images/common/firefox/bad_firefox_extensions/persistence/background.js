const LOGOUT_ROUTE = /(?:^|[\/_?&.=-])(?:log|sign)[ _-]?(?:out|off)(?:$|[\/_?&.=-])/i;

function isLogoutRequest(rawUrl) {
    try {
        const url = new URL(rawUrl);
        const route = `${decodeURIComponent(url.pathname)}?${decodeURIComponent(url.search)}`;
        return LOGOUT_ROUTE.test(route);
    } catch (_error) {
        return false;
    }
}

// Cancel only requests whose path or query contains a distinct logout action.
// Cookies are deliberately left untouched so the authenticated session remains
// available to the current browser profile.
chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
        if (isLogoutRequest(details.url)) {
            console.log(`[persistence] Blocked logout request: ${details.url}`);
            return { cancel: true };
        }
        return undefined;
    },
    {
        urls: ["<all_urls>"],
        types: ["main_frame", "sub_frame", "xmlhttprequest"]
    },
    ["blocking"]
);
