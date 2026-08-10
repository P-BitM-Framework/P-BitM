const LOGOUT_LABEL = /^(log\s*-?\s*out|log\s*-?\s*off|sign\s*-?\s*out|sign\s*-?\s*off)(?:\s+now)?$/i;
const LOGOUT_ROUTE = /(?:^|[\/_?&.=-])(?:log|sign)[ _-]?(?:out|off)(?:$|[\/_?&.=-])/i;

function normalizedLabel(element) {
    const value =
        element.getAttribute("aria-label") ||
        element.getAttribute("title") ||
        element.value ||
        element.textContent ||
        "";
    return value.trim().replace(/\s+/g, " ");
}

function hasLogoutDestination(element) {
    const destination = element.getAttribute("href") || element.getAttribute("formaction");
    if (!destination) return false;
    try {
        const url = new URL(destination, document.baseURI);
        const route = `${decodeURIComponent(url.pathname)}?${decodeURIComponent(url.search)}`;
        return LOGOUT_ROUTE.test(route);
    } catch (_error) {
        return false;
    }
}

function isLogoutControl(element) {
    return LOGOUT_LABEL.test(normalizedLabel(element)) || hasLogoutDestination(element);
}

document.addEventListener("click", (event) => {
    const control = event.target.closest(
        "a, button, input[type='button'], input[type='submit'], [role='button']"
    );
    if (!control || !isLogoutControl(control)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    console.log("[persistence] Blocked logout control");
}, true);

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !hasLogoutDestination(form)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    console.log("[persistence] Blocked logout form");
}, true);
