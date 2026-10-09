import { useOutletContext } from "react-router-dom";

import type { DashboardSettings, SettingsUpdateRequest } from "@/features/settings/schemas";

/** What every section's cards need from the page: the loaded settings and the one save path. */
export type SettingsSectionContext = {
  settings: DashboardSettings;
  /** A settings write is in flight. */
  saving: boolean;
  /** Controls are read-only: a write is in flight or the session cannot write. */
  controlsDisabled: boolean;
  onSave: (payload: SettingsUpdateRequest) => Promise<void>;
  refetchSettings: () => Promise<unknown>;
};

/** The open section's context, provided by the settings layout's outlet. */
export function useSettingsSection(): SettingsSectionContext {
  return useOutletContext<SettingsSectionContext>();
}
