import { lazy, Suspense, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppHeader } from "@/components/layout/app-header";
import { routePermission } from "@/components/layout/nav-items";
import {
  NotFoundPage,
  RouteErrorBoundary,
  RouteLoading,
} from "@/components/layout/route-recovery";
import { RouteScrollRestoration } from "@/components/layout/route-scroll-restoration";
import {
  STATUS_BAR_DEFAULT_HEIGHT_PX,
  StatusBar,
} from "@/components/layout/status-bar";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthGate } from "@/features/auth/components/auth-gate";
import { StepUpDialog } from "@/features/auth/components/step-up-dialog";
import { hasPermission, useAuthStore } from "@/features/auth/hooks/use-auth";
import { signedInLoginDestination } from "@/features/auth/oidc-window";
import { DEFAULT_SETTINGS_SECTION } from "@/features/settings/settings-links";
import { useTimeFormatStore } from "@/hooks/use-time-format";

// Route-level code splitting: only the visited page's chunk loads, instead
// of one entry bundle carrying every page's code.
const DashboardPage = lazy(() =>
  import("@/features/dashboard/components/dashboard-page").then((m) => ({ default: m.DashboardPage })),
);
const LogsPage = lazy(() =>
  import("@/features/logs/components/logs-page").then((m) => ({ default: m.LogsPage })),
);
const ReportsPage = lazy(() =>
  import("@/features/reports/components/reports-page").then((m) => ({ default: m.ReportsPage })),
);
const AccountsPage = lazy(() =>
  import("@/features/accounts/components/accounts-page").then((m) => ({ default: m.AccountsPage })),
);
const ApisPage = lazy(() => import("@/features/apis/components/apis-page").then((m) => ({ default: m.ApisPage })));
const SettingsLayout = lazy(() =>
  import("@/features/settings/components/settings-layout").then((m) => ({ default: m.SettingsLayout })),
);
const settingsSections = () => import("@/features/settings/components/settings-sections");
const GeneralSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.GeneralSettingsSection })));
const AccountsSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.AccountsSettingsSection })));
const AccessSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.AccessSettingsSection })));
const RoutingSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.RoutingSettingsSection })));
const ModelsSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.ModelsSettingsSection })));
const UpstreamSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.UpstreamSettingsSection })));
const DataSettingsSection = lazy(() => settingsSections().then((m) => ({ default: m.DataSettingsSection })));
const NotificationsSettingsSection = lazy(() =>
  settingsSections().then((m) => ({ default: m.NotificationsSettingsSection })),
);
const OrganisationSettingsSection = lazy(() =>
  import("@/features/settings/components/organisation/organisation-section").then((m) => ({
    default: m.OrganisationSettingsSection,
  })),
);
const AutomationsSettingsSection = lazy(() =>
  import("@/features/automations/components/automations-section").then((m) => ({
    default: m.AutomationsSettingsSection,
  })),
);

// Route guard: a page whose nav item the session cannot use is not rendered.
// `/dashboard` is the fallback (every assignable role holds `dashboard:read`);
// when even that is missing the not-found surface renders instead of looping.
function RouteGuard() {
  const { pathname } = useLocation();
  const permissions = useAuthStore((state) => state.permissions);
  const required = routePermission(pathname);
  if (required !== null && !hasPermission(permissions, required)) {
    return pathname === "/dashboard" ? <NotFoundPage /> : <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

function AppLayout() {
  const { hash, key: locationKey, pathname, search } = useLocation();
  const logout = useAuthStore((state) => state.logout);
  const passwordRequired = useAuthStore((state) => state.passwordRequired);
  const role = useAuthStore((state) => state.role);
  const guestPasswordRequired = useAuthStore((state) => state.guestPasswordRequired);
  const startAdminLogin = useAuthStore((state) => state.startAdminLogin);
  const timeFormat = useTimeFormatStore((state) => state.timeFormat);
  const isGuest = role === "guest";
  const [statusBarHeight, setStatusBarHeight] = useState(STATUS_BAR_DEFAULT_HEIGHT_PX);

  return (
    <div
      className="flex min-h-screen flex-col bg-background"
      data-time-format={timeFormat}
      style={{ paddingBottom: statusBarHeight }}
    >
      <RouteScrollRestoration />
      <AppHeader
        onLogout={() => {
          void logout();
        }}
        onAdminLogin={startAdminLogin}
        showAdminLogin={isGuest && passwordRequired}
        showLogout={(role === "admin" && passwordRequired) || (isGuest && guestPasswordRequired)}
      />
      <main className="mx-auto flex w-full max-w-[1500px] flex-1 flex-col px-4 py-8 sm:px-6">
        {/* Keyed by the top-level page, so moving between Settings sections
            keeps the Settings layout mounted; `resetKey` still clears an
            error on every navigation. */}
        <RouteErrorBoundary
          key={pathname.split("/")[1]}
          resetKey={`${locationKey}:${pathname}${search}${hash}`}
        >
          <Suspense fallback={<RouteLoading />}>
            <Outlet />
          </Suspense>
        </RouteErrorBoundary>
      </main>
      <StatusBar onHeightChange={setStatusBarHeight} />
    </div>
  );
}

export default function App() {
  return (
    <TooltipProvider>
      <Toaster richColors />
      <StepUpDialog />
      <AuthGate>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            {/* Public pending screen: once the account exists, "Try again" lands in the app. */}
            <Route path="/auth/pending" element={<Navigate to="/dashboard" replace />} />
            {/* Public login route (`?local=1` is the break-glass form): a session
                that already exists belongs in the app, not on a not-found page —
                and, when a same-tab sign-in flow it started failed here, back on
                the card that started it rather than on the dashboard. */}
            <Route path="/login" element={<Navigate to={signedInLoginDestination()} replace />} />
            <Route element={<RouteGuard />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/accounts" element={<AccountsPage />} />
              <Route path="/apis" element={<ApisPage />} />
              <Route path="/settings" element={<SettingsLayout />}>
                <Route index element={<Navigate to={DEFAULT_SETTINGS_SECTION} replace />} />
                <Route path="general" element={<GeneralSettingsSection />} />
                <Route path="accounts" element={<AccountsSettingsSection />} />
                <Route path="access" element={<AccessSettingsSection />} />
                <Route path="organisation" element={<OrganisationSettingsSection />} />
                <Route path="routing" element={<RoutingSettingsSection />} />
                <Route path="models" element={<ModelsSettingsSection />} />
                <Route path="upstream" element={<UpstreamSettingsSection />} />
                <Route path="automations" element={<AutomationsSettingsSection />} />
                <Route path="data" element={<DataSettingsSection />} />
                <Route path="notifications" element={<NotificationsSettingsSection />} />
              </Route>
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthGate>
    </TooltipProvider>
  );
}
