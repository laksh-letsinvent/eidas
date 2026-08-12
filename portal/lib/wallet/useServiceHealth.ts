"use client";

import { useEffect, useState } from "react";
import { checkServiceHealth } from "./api";

export type ServiceHealth = "checking" | "up" | "down";

/** Probed once per page load — Try It switches quietly between live and
 * recorded-fallback rendering based on this, never showing an error state
 * to a visitor who was never going to have `service/` running locally. */
export function useServiceHealth(): ServiceHealth {
  const [health, setHealth] = useState<ServiceHealth>("checking");

  useEffect(() => {
    let cancelled = false;
    checkServiceHealth().then((up) => {
      if (!cancelled) setHealth(up ? "up" : "down");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return health;
}
