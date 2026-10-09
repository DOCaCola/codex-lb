import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * Scrolls the card named by the location hash into view once `ready` is true.
 * Sections whose cards sit behind a loading state pass their loading flag, so
 * a cold deep link still lands on the card. A hash that names no element (a
 * tab or sheet selector such as `#people`) leaves the page where it is.
 */
export function useHashTargetScroll(ready: boolean) {
  const { hash, key: locationKey } = useLocation();

  useEffect(() => {
    if (!ready || hash === "") {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView({ block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [hash, locationKey, ready]);
}
