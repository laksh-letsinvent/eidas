// Hand-rolled service worker for the /wallet PWA — no Workbox/next-pwa, same
// "no library where the mechanism is the point" pattern as the hand-rolled
// JWT in Phase 1. Cache-first for the wallet route and its static chunks,
// populated on first visit rather than a hardcoded precache list (static
// export produces content-hashed filenames that would drift every build).
//
// Deliberately never intercepts calls to the verifier service (localhost —
// a different origin, so same-origin-only guard below already excludes it).
// Offline support here means "the wallet view still renders the held
// credential," not "presentation works offline" — presentation inherently
// needs a live verifier.

const CACHE_NAME = "eidas-wallet-v1";
const PRECACHE_URLS = ["/wallet/", "/manifest.json", "/icons/wallet.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function isInScope(url) {
  return (
    url.pathname.startsWith("/wallet") ||
    url.pathname.startsWith("/_next/static/") ||
    url.pathname === "/manifest.json" ||
    url.pathname.startsWith("/icons/")
  );
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || !isInScope(url)) {
    return; // not ours to intercept — let the browser handle it normally
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
