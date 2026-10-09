import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { InheritBadge } from "@/features/settings/components/inherit-badge";
import { useSettingsSection } from "@/features/settings/use-settings-section";
import { buildSettingsUpdateRequest } from "@/features/settings/payload";

const SWITCH_ID = "automations-pause-all";

/**
 * "Pause all automations", the first card of Settings → Automations and the
 * dashboard's only control for `automations_scheduler_enabled`.
 *
 * On pauses the scheduler tick and refuses manual runs on every replica from
 * the next tick, without a restart. The inheritance badge and reset action are
 * the shared ones. Writing the setting needs write access, so a read-only
 * viewer sees the state but cannot flip it.
 */
export function AutomationsPauseToggle() {
  const { t } = useTranslation();
  const { settings, controlsDisabled, onSave } = useSettingsSection();
  const paused = !settings.automationsSchedulerEnabled;

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border bg-card p-5">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Label htmlFor={SWITCH_ID} className="text-sm font-medium">
            {t("automations.pause.label")}
          </Label>
          {paused ? <Badge variant="destructive">{t("automations.pause.badge")}</Badge> : null}
        </div>
        <p className="text-xs text-muted-foreground">
          {paused ? t("automations.pause.pausedDescription") : t("automations.pause.description")}
        </p>
        {/*
          The badge reports the provenance of `automations_scheduler_enabled`,
          whose on/off is the inverse of this switch's "paused"; the caption
          names the setting so "(on)" is never read as "paused".
        */}
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">{t("automations.pause.inheritPrefix")}</span>
          <InheritBadge
            settings={settings}
            name="automations_scheduler_enabled"
            field="automationsSchedulerEnabled"
            busy={controlsDisabled}
            onSave={onSave}
          />
        </span>
      </div>
      <Switch
        id={SWITCH_ID}
        aria-label={t("automations.pause.ariaLabel")}
        checked={paused}
        disabled={controlsDisabled}
        onCheckedChange={(checked) =>
          void onSave(buildSettingsUpdateRequest(settings, { automationsSchedulerEnabled: !checked }))
        }
      />
    </div>
  );
}
