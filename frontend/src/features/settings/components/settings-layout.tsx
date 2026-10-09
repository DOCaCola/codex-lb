import { Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import {
  Bell,
  Building2,
  Clock,
  Database,
  Layers,
  Route,
  Server,
  Settings,
  Shield,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { AlertMessage } from "@/components/alert-message";
import { LoadingOverlay } from "@/components/layout/loading-overlay";
import { RouteLoading } from "@/components/layout/route-recovery";
import { Button } from "@/components/ui/button";
import { hasPermission, useAuthStore } from "@/features/auth/hooks/use-auth";
import { SettingsSkeleton } from "@/features/settings/components/settings-skeleton";
import { useSettings } from "@/features/settings/hooks/use-settings";
import { SETTINGS_SECTIONS, settingsPath, type SettingsSectionId } from "@/features/settings/settings-links";
import type { SettingsSectionContext } from "@/features/settings/use-settings-section";
import { cn } from "@/lib/utils";
import { getErrorMessageOrNull } from "@/utils/errors";

const SECTION_ICONS: Record<SettingsSectionId, LucideIcon> = {
  general: SlidersHorizontal,
  accounts: Users,
  access: Shield,
  organisation: Building2,
  routing: Route,
  models: Layers,
  upstream: Server,
  automations: Clock,
  data: Database,
  notifications: Bell,
};

/** A section's heading and cards. */
export function SettingsSection({
  section,
  description,
  children,
}: {
  section: SettingsSectionId;
  description?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">{t(`settings.sections.${section}`)}</h2>
        {description ? <div className="text-sm text-muted-foreground">{description}</div> : null}
      </div>
      {children}
    </div>
  );
}

function SettingsSideMenu() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navRef = useRef<HTMLElement>(null);
  const permissions = useAuthStore((state) => state.permissions);
  const sections = SETTINGS_SECTIONS.filter(
    (section) => !("requires" in section) || hasPermission(permissions, section.requires),
  );

  // On phones the menu is a horizontal scroller: centre the open section in it.
  // Only the scroller moves, so a hash target the page scrolled to stays put.
  // On wider screens the menu does not scroll and this is a no-op.
  useEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!nav || !active) return;
    const navBox = nav.getBoundingClientRect();
    const activeBox = active.getBoundingClientRect();
    nav.scrollLeft += activeBox.left - navBox.left - (navBox.width - activeBox.width) / 2;
  }, [pathname]);

  return (
    <nav
      ref={navRef}
      aria-label={t("settings.nav.label")}
      className="flex gap-0.5 overflow-x-auto rounded-[10px] bg-muted/50 p-1 [scrollbar-width:none] md:sticky md:top-20 md:flex-col md:overflow-visible md:rounded-none md:bg-transparent md:p-0"
    >
      {sections.map((section, index) => {
        const Icon = SECTION_ICONS[section.id];
        const startsGroup = index === 0 || sections[index - 1].group !== section.group;
        return (
          <div key={section.id} className="contents">
            {startsGroup ? (
              <p
                className={cn(
                  "mx-2.5 mb-1.5 hidden text-[11px] font-semibold tracking-wider text-muted-foreground uppercase md:block",
                  index > 0 && "mt-3.5",
                )}
              >
                {t(`settings.nav.groups.${section.group}`)}
              </p>
            ) : null}
            <NavLink
              to={settingsPath(section.id)}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-1.5 text-[13px] transition-colors md:px-2.5 md:text-sm",
                  isActive
                    ? "bg-background font-medium text-foreground shadow-[var(--shadow-sm)] md:bg-muted md:shadow-none"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {t(`settings.sections.${section.id}`)}
            </NavLink>
          </div>
        );
      })}
    </nav>
  );
}

/**
 * `/settings`: the heading, the notices and the side menu around the open
 * section. The settings document and its save mutation live here so every
 * section saves through one path and shares one saving overlay; data only a
 * section's cards need is fetched by that section, while it is open.
 */
export function SettingsLayout() {
  const { t } = useTranslation();
  const { settingsQuery, updateSettingsMutation } = useSettings();
  const [initialRetryError, setInitialRetryError] = useState<string | null>(null);
  const authMode = useAuthStore((state) => state.authMode);
  const canWrite = useAuthStore((state) => state.canWrite);

  const settings = settingsQuery.data;
  const saving = updateSettingsMutation.isPending;
  const settingsLoadError = getErrorMessageOrNull(settingsQuery.error, t("settings.toasts.loadFailed"));
  const displayedSettingsLoadError = settingsLoadError || initialRetryError;
  // With no settings loaded the failed-load branch below owns this message, so
  // the page-level alert would otherwise render it a second time.
  const error = (settings ? settingsLoadError : null) || getErrorMessageOrNull(updateSettingsMutation.error);

  const context: SettingsSectionContext | null = settings
    ? {
        settings,
        saving,
        controlsDisabled: saving || !canWrite,
        onSave: async (payload) => {
          await updateSettingsMutation.mutateAsync(payload);
        },
        refetchSettings: () => settingsQuery.refetch(),
      }
    : null;

  return (
    <div className="animate-fade-in-up space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Settings className="h-5 w-5 text-primary" />
          {t("settings.page.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("settings.page.subtitle")}</p>
      </div>

      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      {settings && !canWrite ? (
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs font-medium text-foreground">
          {t("settings.page.readOnlyNotice")}
        </div>
      ) : null}
      {settings && authMode === "trusted_header" ? (
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs font-medium text-foreground">
          {t("settings.page.trustedHeaderNotice")}
        </div>
      ) : null}
      {settings && authMode === "disabled" ? (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs font-medium text-foreground">
          {t("settings.page.disabledNotice")}
        </div>
      ) : null}

      <div className="grid items-start gap-4 md:grid-cols-[220px_minmax(0,1fr)] md:gap-8">
        <SettingsSideMenu />
        <div className="min-w-0">
          {context ? (
            <Suspense fallback={<RouteLoading />}>
              <Outlet context={context} />
            </Suspense>
          ) : settingsQuery.isPending && initialRetryError === null ? (
            <SettingsSkeleton />
          ) : (
            <div className="space-y-3 rounded-xl border bg-card p-4">
              <div role="alert">
                <AlertMessage variant="error">
                  {displayedSettingsLoadError || t("settings.toasts.loadFailed")}
                </AlertMessage>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setInitialRetryError(displayedSettingsLoadError || t("settings.toasts.loadFailed"));
                  void settingsQuery.refetch().finally(() => {
                    setInitialRetryError(null);
                  });
                }}
                disabled={settingsQuery.isFetching || initialRetryError !== null}
              >
                {t("common.actions.retry")}
              </Button>
            </div>
          )}
        </div>
      </div>

      <LoadingOverlay visible={saving} label={t("settings.page.savingLabel")} />
    </div>
  );
}
