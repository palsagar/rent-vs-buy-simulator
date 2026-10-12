/*
 * Umami event tracking. The Umami tag is injected server-side only when
 * UMAMI_DOMAIN/UMAMI_ID are set (production); everywhere else — local dev,
 * tests, ad-blocked browsers — window.umami is undefined and trackEvent is a
 * no-op. The try/catch guarantees analytics can never break the app. This
 * module also defines window.umamiBeforeSend, the hook the tag names
 * (server.py).
 */
import { DEFAULT_CONFIG } from "./state.js";

export function trackEvent(name, props) {
    try {
        window.umami?.track(name, props);
    } catch { /* analytics must never break the app */ }
}

// The share-URL params the app writes into the address bar (state.js).
// Other params, such as utm_* and ref, are campaign data and stay.
const APP_PARAMS = [...Object.keys(DEFAULT_CONFIG), "r", "ftb", "v"];

function stripAppParams(url) {
    const u = new URL(url);
    for (const key of APP_PARAMS) u.searchParams.delete(key);
    return u.toString();
}

// The address bar as the visitor landed. This module runs before main.js,
// and the app's first address-bar write is debounced (state.js), so this
// is always the URL before the app rewrites it. A slow tracker can start
// after that write and report the rewritten URL as the first page view.
const LANDING_URL = location.href;

let lastPageViewPath = null;

/*
 * The tag's data-before-send hook (server.py). Umami sends a page view
 * every time the app rewrites the address bar, so without this every slider
 * release would count as a visit to its own unique URL. Page views are the
 * "event" payloads without a name; one is sent per page load.
 */
window.umamiBeforeSend = (type, payload) => {
    try {
        if (type === "event" && !payload.name) {
            const first = lastPageViewPath === null;
            if (first) payload.url = LANDING_URL;
            // By path, not full URL: the app's first address-bar write drops
            // a landing link's utm_* params, which is not a new page.
            const url = new URL(payload.url || location.href);
            if (url.pathname === lastPageViewPath) return null;
            // Stripping removes the only sign of a shared link, so report
            // it here. The timeout sends it after this page view.
            if (first && APP_PARAMS.some((k) => url.searchParams.has(k))) {
                setTimeout(() => trackEvent("link-opened"), 0);
            }
            lastPageViewPath = url.pathname;
        }
        if (payload.url) payload.url = stripAppParams(payload.url);
        // Every referrer: after the first address-bar write it is the
        // previous URL on this site, with the visitor's inputs in it.
        if (payload.referrer) payload.referrer = stripAppParams(payload.referrer);
    } catch { /* analytics must never break the app */ }
    return payload;
};
