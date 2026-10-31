import { useState } from "react";

const COLLAPSED_KEY = "codex-lb.providers.rail-collapsed";

/** Collapsed state of the account rail, kept across visits. */
export function useRailCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSED_KEY) === "1");
  const toggle = () => {
    localStorage.setItem(COLLAPSED_KEY, collapsed ? "0" : "1");
    setCollapsed(!collapsed);
  };
  return [collapsed, toggle];
}
