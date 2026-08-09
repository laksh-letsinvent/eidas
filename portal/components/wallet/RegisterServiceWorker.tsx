"use client";

import { useEffect } from "react";

/** Mounted only under app/wallet — scopes service-worker registration (and
 * therefore offline support) to the wallet route, not the whole portal.
 *
 * Deliberately skipped outside production: `next dev`/Turbopack recompiles
 * JS chunks on every request under content-hashed names that change
 * constantly, which a cache-first SW fights with — caching a dev chunk and
 * serving it after the next recompile causes a version mismatch that forces
 * repeated full reloads. Real offline support is only meaningful (and only
 * tested) against the static-export production build. */
export function RegisterServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/wallet/" }).catch((err) => {
      console.error("[wallet] service worker registration failed", err);
    });
  }, []);

  return null;
}
