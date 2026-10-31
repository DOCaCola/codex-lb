import { useMatch } from "react-router-dom";

export type DetailTab = "overview" | "settings";

/** Tab of the open account page, carried in the URL so links and reloads keep it. */
export function useDetailTab(): DetailTab {
  return useMatch("/providers/:accountId/settings") ? "settings" : "overview";
}
