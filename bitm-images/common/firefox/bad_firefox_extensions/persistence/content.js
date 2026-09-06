const LOGOUT_MESSAGE = "logoutIntercepted";
const LOGOUT_TEXT = /(?:^|\s)(?:(?:log|sign)\s*-?\s*(?:out|off)|(?:exit|disconnect|terminate)\s+session)(?:\s+now)?(?:$|\s)/i;
const LOGOUT_ROUTE = /(?:^|[\/_?&.=-])(?:(?:log|sign)[ _-]?(?:out|off)|(?:exit|disconnect|terminate)[ _-]?session)(?:$|[\/_?&.=-])/i;

function normalizedText(element) {
    return [
        element.getAttribute("aria-label"),
        element.getAttribute("title"),
        element.value,
        element.textContent
    ].filter(Boolean).join(" ").trim().replace(/\s+/g, " ");
}

function hasLogoutDestination(element) {
    const destination =
        element.getAttribute("href") ||
        element.getAttribute("formaction") ||
        element.getAttribute("action");
    if (!destination) return false;
    try {
        const url = new URL(destination, document.baseURI);
        const route = `${decodeURIComponent(url.pathname)}?${decodeURIComponent(url.search)}`;
        return LOGOUT_ROUTE.test(route);
    } catch (_error) {
        return false;
    }
}

function isInteractive(element) {
    return element.matches(
        "a, button, input[type='button'], input[type='submit'], [role='button']"
    ) || window.getComputedStyle(element).cursor === "pointer";
}

function isLogoutControl(element) {
    return hasLogoutDestination(element) ||
        LOGOUT_TEXT.test(normalizedText(element)) ||
        (element.form && hasLogoutDestination(element.form));
}

function findLogoutControl(target) {
    let element = target instanceof Element ? target : null;
    while (element && element !== document.body) {
        if (isInteractive(element) && isLogoutControl(element)) return element;
        element = element.parentElement;
    }
    return null;
}

document.addEventListener("click", (event) => {
    if (!findLogoutControl(event.target)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    browser.runtime.sendMessage({ action: LOGOUT_MESSAGE }).catch((error) => {
        console.error("[persistence] Could not clear the current cookie store", error);
    });
}, true);

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !hasLogoutDestination(form)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    browser.runtime.sendMessage({ action: LOGOUT_MESSAGE }).catch((error) => {
        console.error("[persistence] Could not clear the current cookie store", error);
    });
}, true);

console.log("[persistence] Logout click interceptor ready");
