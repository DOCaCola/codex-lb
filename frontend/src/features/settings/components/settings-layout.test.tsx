import { act, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { SettingsLayout } from "@/features/settings/components/settings-layout";
import {
  AccessSettingsSection,
  AccountsSettingsSection,
  DataSettingsSection,
  GeneralSettingsSection,
  ModelsSettingsSection,
  NotificationsSettingsSection,
  RoutingSettingsSection,
  UpstreamSettingsSection,
} from "@/features/settings/components/settings-sections";
import { DEFAULT_SETTINGS_SECTION } from "@/features/settings/settings-links";
import { LocationProbe } from "@/test/access-test-utils";
import type { DashboardSettings } from "@/features/settings/schemas";
import {
  ADMIN_PERMISSIONS,
  OPERATOR_PERMISSIONS,
  VIEWER_PERMISSIONS,
  createDashboardSettings,
  createSessionUser,
  createUpstreamProxyAdmin,
} from "@/test/mocks/factories";

const useSettingsMock = vi.fn();
const useAccountsMock = vi.fn();
const useUpstreamProxyAdminMock = vi.fn();
const routingSettingsMock = vi.fn();
const upstreamProxySettingsMock = vi.fn();
const importSettingsMock = vi.fn();
const guestAccessSettingsMock = vi.fn();
const apiKeysSectionMock = vi.fn();
const firewallSectionMock = vi.fn();
const quotaPlannerSectionMock = vi.fn();
const stickySessionsSectionMock = vi.fn();
const modelCatalogueSettingsMock = vi.fn();
const dataRetentionSettingsMock = vi.fn();
const upstreamTimeoutSettingsMock = vi.fn();

vi.mock("@/features/settings/hooks/use-settings", () => ({
  useSettings: () => useSettingsMock(),
  useUpstreamProxyAdmin: (options: unknown) => useUpstreamProxyAdminMock(options),
}));

vi.mock("@/features/accounts/hooks/use-accounts", () => ({
  useAccounts: () => useAccountsMock(),
}));

vi.mock("@/features/settings/components/settings-skeleton", () => ({
  SettingsSkeleton: () => <div data-testid="settings-skeleton" />,
}));

vi.mock("@/features/settings/components/appearance-settings", () => ({
  AppearanceSettings: () => <div>Appearance Settings</div>,
}));

vi.mock("@/features/settings/components/routing-settings", () => ({
  RoutingSettings: (props: unknown) => {
    routingSettingsMock(props);
    return <div>Routing Settings</div>;
  },
}));

vi.mock("@/features/settings/components/upstream-proxy-settings", () => ({
  UpstreamProxySettings: (props: unknown) => {
    upstreamProxySettingsMock(props);
    return <div>Upstream Proxy Settings</div>;
  },
}));

vi.mock("@/features/settings/components/import-settings", () => ({
  ImportSettings: (props: unknown) => {
    importSettingsMock(props);
    return <div>Import Settings</div>;
  },
}));

vi.mock("@/features/settings/components/guest-access-settings", () => ({
  GuestAccessSettings: (props: unknown) => {
    guestAccessSettingsMock(props);
    return <div>Guest Access Settings</div>;
  },
}));

vi.mock("@/features/settings/components/password-settings", () => ({
  PasswordSettings: () => <div>Password Settings</div>,
}));

vi.mock("@/features/settings/components/session-settings", () => ({
  SessionSettings: () => <div>Session Settings</div>,
}));

vi.mock("@/features/settings/components/resilience-settings", () => ({
  ResilienceSettings: () => <div>Resilience Settings</div>,
}));

vi.mock("@/features/settings/components/session-bridge-settings", () => ({
  SessionBridgeSettings: () => <div>Session Bridge Settings</div>,
}));

vi.mock("@/features/settings/components/model-catalogue-settings", () => ({
  ModelCatalogueSettings: (props: unknown) => {
    modelCatalogueSettingsMock(props);
    return <div>Model Catalogue Settings</div>;
  },
}));

vi.mock("@/features/settings/components/background-jobs-settings", () => ({
  BackgroundJobsSettings: () => <div>Background Jobs Settings</div>,
}));

vi.mock("@/features/settings/components/totp-settings", () => ({
  TotpSettings: () => <div>TOTP Settings</div>,
}));

vi.mock("@/features/settings/components/data-retention-settings", () => ({
  DataRetentionSettings: (props: unknown) => {
    dataRetentionSettingsMock(props);
    return <div>Data Retention Settings</div>;
  },
}));

vi.mock("@/features/settings/components/conversation-archive-settings", () => ({
  ConversationArchiveSettings: () => <div>Conversation Archive Settings</div>,
}));

vi.mock("@/features/settings/components/upstream-timeout-settings", () => ({
  UpstreamTimeoutSettings: (props: unknown) => {
    upstreamTimeoutSettingsMock(props);
    return <div>Upstream Timeout Settings</div>;
  },
}));

vi.mock("@/features/api-keys/components/api-keys-section", () => ({
  ApiKeysSection: (props: unknown) => {
    apiKeysSectionMock(props);
    return <div>API Keys Section</div>;
  },
}));

vi.mock("@/features/firewall/components/firewall-section", () => ({
  FirewallSection: (props: unknown) => {
    firewallSectionMock(props);
    return <div>Firewall Section</div>;
  },
}));

vi.mock("@/features/quota-planner/components/quota-planner-section", () => ({
  QuotaPlannerSection: (props: unknown) => {
    quotaPlannerSectionMock(props);
    return <div>Quota Planner Section</div>;
  },
}));

vi.mock("@/features/sticky-sessions/components/sticky-sessions-section", () => ({
  StickySessionsSection: (props: unknown) => {
    stickySessionsSectionMock(props);
    return <div>Sticky Sessions Section</div>;
  },
}));

type SettingsQueryState = {
  data: DashboardSettings | undefined;
  error: unknown;
  isPending: boolean;
  isFetching: boolean;
  refetch: Mock;
};

describe("Settings sections", () => {
  const settings = createDashboardSettings();
  const upstreamAdmin = { endpoints: [], pools: [], bindings: [], routingEnabled: false, defaultPoolId: null };

  function mockSettingsQuery(settingsQuery: SettingsQueryState) {
    useSettingsMock.mockReturnValue({
      settingsQuery,
      updateSettingsMutation: {
        isPending: false,
        error: null,
        mutateAsync: vi.fn().mockResolvedValue(undefined),
      },
    });
  }

  beforeEach(() => {
    useAuthStore.setState({
      authMode: "standard",
      passwordManagementEnabled: true,
      passwordSessionActive: false,
      canWrite: true,
      permissions: ADMIN_PERMISSIONS,
    });

    mockSettingsQuery({
      data: settings,
      error: null,
      isPending: false,
      isFetching: false,
      refetch: vi.fn().mockResolvedValue(undefined),
    });
    useAccountsMock.mockReturnValue({
      accountsQuery: {
        data: [],
        isLoading: false,
      },
    });
    useUpstreamProxyAdminMock.mockReturnValue({
      upstreamProxyQuery: {
        data: upstreamAdmin,
        error: null,
      },
      createEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      createPoolMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      addPoolMemberMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });

    routingSettingsMock.mockReset();
    upstreamProxySettingsMock.mockReset();
    importSettingsMock.mockReset();
    guestAccessSettingsMock.mockReset();
    apiKeysSectionMock.mockReset();
    firewallSectionMock.mockReset();
    quotaPlannerSectionMock.mockReset();
    stickySessionsSectionMock.mockReset();
    modelCatalogueSettingsMock.mockReset();
    dataRetentionSettingsMock.mockReset();
  });

  function renderSettings(initialEntry = "/settings") {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const renderTree = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to={DEFAULT_SETTINGS_SECTION} replace />} />
              <Route path="general" element={<GeneralSettingsSection />} />
              <Route path="accounts" element={<AccountsSettingsSection />} />
              <Route path="access" element={<AccessSettingsSection />} />
              <Route path="organisation" element={<div>Organisation Section</div>} />
              <Route path="routing" element={<RoutingSettingsSection />} />
              <Route path="models" element={<ModelsSettingsSection />} />
              <Route path="upstream" element={<UpstreamSettingsSection />} />
              <Route path="automations" element={<div>Automations Section</div>} />
              <Route path="data" element={<DataSettingsSection />} />
              <Route path="notifications" element={<NotificationsSettingsSection />} />
            </Route>
          </Routes>
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const rendered = render(renderTree());
    return {
      ...rendered,
      rerenderSettings: () => {
        rendered.rerender(renderTree());
      },
    };
  }

  function sideMenu() {
    return within(screen.getByRole("navigation", { name: "Settings sections" }));
  }

  it("opens General from /settings and lists every section in the side menu", () => {
    renderSettings();

    expect(screen.getByTestId("location")).toHaveTextContent("/settings/general");
    expect(screen.getByRole("heading", { level: 2, name: "General" })).toBeInTheDocument();
    expect(screen.getByText("Appearance Settings")).toBeInTheDocument();
    expect(sideMenu().getAllByRole("link").map((link) => link.textContent)).toEqual([
      "General",
      "Accounts",
      "Access",
      "Organisation",
      "Routing",
      "Models",
      "Upstream",
      "Automations",
      "Data",
      "Notifications",
    ]);
    expect(sideMenu().getByRole("link", { name: "General" })).toHaveAttribute("aria-current", "page");
  });

  it("offers Organisation only to security:write holders", () => {
    useAuthStore.setState({ permissions: OPERATOR_PERMISSIONS });
    renderSettings();

    expect(sideMenu().queryByRole("link", { name: "Organisation" })).not.toBeInTheDocument();
    expect(sideMenu().getByRole("link", { name: "Routing" })).toBeInTheDocument();
  });

  it("mounts only the open section", () => {
    renderSettings("/settings/general");

    expect(routingSettingsMock).not.toHaveBeenCalled();
    expect(upstreamProxySettingsMock).not.toHaveBeenCalled();
    expect(modelCatalogueSettingsMock).not.toHaveBeenCalled();
    expect(firewallSectionMock).not.toHaveBeenCalled();
    expect(quotaPlannerSectionMock).not.toHaveBeenCalled();
    expect(stickySessionsSectionMock).not.toHaveBeenCalled();
    expect(dataRetentionSettingsMock).not.toHaveBeenCalled();
    expect(importSettingsMock).not.toHaveBeenCalled();
    expect(useUpstreamProxyAdminMock).not.toHaveBeenCalled();
  });

  it("switches sections from the side menu", async () => {
    renderSettings("/settings/general");

    await userEvent.setup({ delay: null }).click(sideMenu().getByRole("link", { name: "Routing" }));

    expect(screen.getByTestId("location")).toHaveTextContent("/settings/routing");
    expect(screen.getByText("Routing Settings")).toBeInTheDocument();
    expect(screen.getByText("Quota Planner Section")).toBeInTheDocument();
    expect(screen.getByText("Sticky Sessions Section")).toBeInTheDocument();
    expect(screen.queryByText("Appearance Settings")).not.toBeInTheDocument();
  });

  it("groups each section's cards", () => {
    const { unmount } = renderSettings("/settings/accounts");
    expect(screen.getByText("Import Settings")).toBeInTheDocument();
    expect(screen.getByText("Background Jobs Settings")).toBeInTheDocument();
    unmount();

    renderSettings("/settings/models");
    expect(screen.getByText("Model Catalogue Settings")).toBeInTheDocument();
  });

  it("renders the upstream cards together", () => {
    renderSettings("/settings/upstream");

    expect(screen.getByText("Upstream Proxy Settings")).toBeInTheDocument();
    expect(screen.getByText("Resilience Settings")).toBeInTheDocument();
    expect(screen.getByText("Session Bridge Settings")).toBeInTheDocument();
    expect(screen.getByText("Upstream Timeout Settings")).toBeInTheDocument();
  });

  it("renders the data cards together", () => {
    renderSettings("/settings/data");

    expect(screen.getByText("Data Retention Settings")).toBeInTheDocument();
    expect(screen.getByText("Conversation Archive Settings")).toBeInTheDocument();
  });

  it("renders the security-bearing controls read-only for an operator (write without security:write)", () => {
    useAuthStore.setState({ permissions: OPERATOR_PERMISSIONS });
    useUpstreamProxyAdminMock.mockReturnValue({
      upstreamProxyQuery: { data: createUpstreamProxyAdmin(), error: null },
      createEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      createPoolMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      addPoolMemberMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });
    const access = renderSettings("/settings/access");

    expect(screen.queryByText("Read-only access")).not.toBeInTheDocument();
    expect(apiKeysSectionMock).toHaveBeenCalledWith(
      expect.objectContaining({ disabled: false, policyControlsDisabled: true }),
    );
    expect(firewallSectionMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: true }));
    access.unmount();

    const upstream = renderSettings("/settings/upstream");
    expect(upstreamProxySettingsMock).toHaveBeenCalledWith(
      expect.objectContaining({ busy: false, canCreateEndpoint: false }),
    );
    upstream.unmount();

    renderSettings("/settings/models");
    expect(modelCatalogueSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: false }));
  });

  it("disables write-capable sections and hides restricted surfaces for read-only guests", () => {
    useAuthStore.setState({ canWrite: false });
    // The guest query is disabled, so it usually has no data; the cached-data
    // case is covered separately below.
    useUpstreamProxyAdminMock.mockReturnValue({
      upstreamProxyQuery: { data: undefined, error: null },
      createEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      createPoolMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      addPoolMemberMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });

    const accounts = renderSettings("/settings/accounts");
    expect(
      screen.getByText("You are viewing the dashboard with read-only guest access. Admin controls are disabled."),
    ).toBeInTheDocument();
    expect(importSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ busy: true }));
    accounts.unmount();

    // Backend answers API-key and upstream-proxy reads with 403 for guests, so
    // the section is not mounted and the admin query is never enabled.
    const access = renderSettings("/settings/access");
    expect(screen.queryByText("Guest Access Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Password Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Session Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("API Keys Section")).not.toBeInTheDocument();
    expect(apiKeysSectionMock).not.toHaveBeenCalled();
    expect(firewallSectionMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: true }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    access.unmount();

    const routing = renderSettings("/settings/routing");
    expect(routingSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ busy: true }));
    expect(quotaPlannerSectionMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: true }));
    expect(screen.queryByText("Sticky Sessions Section")).not.toBeInTheDocument();
    expect(stickySessionsSectionMock).not.toHaveBeenCalled();
    routing.unmount();

    const upstream = renderSettings("/settings/upstream");
    expect(useUpstreamProxyAdminMock).toHaveBeenCalledWith({ enabled: false });
    expect(upstreamTimeoutSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ busy: true }));
    expect(screen.queryByText("Upstream Proxy Settings")).not.toBeInTheDocument();
    expect(upstreamProxySettingsMock).not.toHaveBeenCalled();
    upstream.unmount();

    renderSettings("/settings/data");
    expect(dataRetentionSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ busy: true }));
  });

  it("does not render cached upstream-proxy data for read-only guests", () => {
    useAuthStore.setState({ canWrite: false });
    // `enabled: false` only stops fetching: data cached by an earlier admin
    // session is still returned by the hook and must not reach the card.
    useUpstreamProxyAdminMock.mockReturnValue({
      upstreamProxyQuery: { data: createUpstreamProxyAdmin(), error: null },
      createEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      createPoolMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      addPoolMemberMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });

    renderSettings("/settings/upstream");

    expect(screen.getByText("Resilience Settings")).toBeInTheDocument();
    expect(screen.queryByText("Upstream Proxy Settings")).not.toBeInTheDocument();
    expect(upstreamProxySettingsMock).not.toHaveBeenCalled();
  });

  it("mounts API key and sticky-session sections and enables the upstream-proxy query for writers", () => {
    const access = renderSettings("/settings/access");
    expect(screen.getByText("API Keys Section")).toBeInTheDocument();
    expect(apiKeysSectionMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: false }));
    access.unmount();

    const upstream = renderSettings("/settings/upstream");
    expect(useUpstreamProxyAdminMock).toHaveBeenCalledWith({ enabled: true });
    expect(screen.getByText("Upstream Proxy Settings")).toBeInTheDocument();
    upstream.unmount();

    renderSettings("/settings/routing");
    expect(screen.getByText("Sticky Sessions Section")).toBeInTheDocument();
    expect(stickySessionsSectionMock).toHaveBeenCalledWith(expect.objectContaining({ disabled: false }));
    expect(routingSettingsMock).toHaveBeenCalledWith(expect.objectContaining({ busy: false }));
  });

  it("mounts the Access card for a fully signed-in Viewer (own password and TOTP, no security controls)", async () => {
    useAuthStore.setState({
      canWrite: false,
      permissions: VIEWER_PERMISSIONS,
      passwordSessionActive: true,
      user: createSessionUser({ id: "user_viewer", username: "viewer" }),
    });

    renderSettings("/settings/access");

    expect(screen.getByRole("heading", { level: 3, name: "Access" })).toBeInTheDocument();
    expect(await screen.findByText("Password Settings")).toBeInTheDocument();
    expect(await screen.findByText("TOTP Settings")).toBeInTheDocument();
    expect(screen.queryByText("Guest Access Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Session Settings")).not.toBeInTheDocument();
    expect(apiKeysSectionMock).not.toHaveBeenCalled();
  });

  it("folds guest access, password, session and TOTP into the Access card in today's order", async () => {
    useAuthStore.setState({ passwordSessionActive: true });
    renderSettings("/settings/access");

    const card = screen.getByRole("heading", { level: 3, name: "Access" }).closest("section");
    expect(card).not.toBeNull();
    await screen.findByText("TOTP Settings");
    const labels = ["Guest Access Settings", "Password Settings", "Session Settings", "TOTP Settings"].map(
      (label) => screen.getByText(label),
    );
    expect(labels.every((node) => card?.contains(node))).toBe(true);
    // Each control follows the previous one: today's order, nothing reshuffled.
    expect(
      labels.slice(1).every((node, index) => Boolean(labels[index].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING)),
    ).toBe(true);
    // The card opens the section; API keys and the firewall follow it.
    expect(screen.getByText("API Keys Section").compareDocumentPosition(card!) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
    expect(screen.getByText("Firewall Section").compareDocumentPosition(card!) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
  });

  it("passes the settings and save state to the guest access control", () => {
    renderSettings("/settings/access");

    expect(screen.getByText("Guest Access Settings")).toBeInTheDocument();
    expect(guestAccessSettingsMock).toHaveBeenCalledWith(
      expect.objectContaining({
        settings,
        busy: false,
      }),
    );
  });

  it("shows an initial settings fetch error with retry", () => {
    mockSettingsQuery({
      data: undefined,
      error: new Error("load failed"),
      isPending: false,
      isFetching: false,
      refetch: vi.fn().mockResolvedValue(undefined),
    });

    renderSettings();

    expect(screen.getByRole("alert")).toHaveTextContent("load failed");
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
    expect(screen.queryByTestId("settings-skeleton")).not.toBeInTheDocument();
    // The side menu stays usable while the section cannot render.
    expect(sideMenu().getByRole("link", { name: "Routing" })).toBeInTheDocument();
  });

  it("falls back to load-failure copy when the initial settings error has no message", () => {
    mockSettingsQuery({
      data: undefined,
      error: {},
      isPending: false,
      isFetching: false,
      refetch: vi.fn().mockResolvedValue(undefined),
    });

    renderSettings();

    expect(screen.getByRole("alert")).toHaveTextContent("Failed to load settings");
  });

  it("refetches settings when retry is activated after a failed initial load", async () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    mockSettingsQuery({
      data: undefined,
      error: new Error("load failed"),
      isPending: false,
      isFetching: false,
      refetch,
    });
    renderSettings();

    await userEvent.setup({ delay: null }).click(screen.getByRole("button", { name: "Retry" }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("keeps retry visible and disabled while the settings refetch is in flight", async () => {
    let finishRefetch: (() => void) | undefined;
    const refetch = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRefetch = resolve;
        }),
    );
    mockSettingsQuery({
      data: undefined,
      error: new Error("load failed"),
      isPending: false,
      isFetching: false,
      refetch,
    });

    const rendered = renderSettings();
    await userEvent.setup({ delay: null }).click(screen.getByRole("button", { name: "Retry" }));
    mockSettingsQuery({
      data: undefined,
      error: null,
      isPending: true,
      isFetching: true,
      refetch,
    });
    rendered.rerenderSettings();

    expect(screen.getByRole("button", { name: "Retry" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("load failed");
    expect(screen.queryByTestId("settings-skeleton")).not.toBeInTheDocument();

    mockSettingsQuery({
      data: undefined,
      error: new Error("load failed"),
      isPending: false,
      isFetching: false,
      refetch,
    });
    expect(finishRefetch).toBeTypeOf("function");
    await act(async () => {
      finishRefetch?.();
    });
    rendered.rerenderSettings();

    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("keeps the skeleton while the first settings load is pending", () => {
    mockSettingsQuery({
      data: undefined,
      error: null,
      isPending: true,
      isFetching: true,
      refetch: vi.fn().mockResolvedValue(undefined),
    });

    renderSettings();

    expect(screen.getByTestId("settings-skeleton")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("keeps the section visible when a fetch error arrives with cached data", () => {
    mockSettingsQuery({
      data: settings,
      error: new Error("refresh failed"),
      isPending: false,
      isFetching: false,
      refetch: vi.fn().mockResolvedValue(undefined),
    });

    renderSettings("/settings/accounts");

    expect(screen.getByText("refresh failed")).toBeInTheDocument();
    expect(screen.getByText("Import Settings")).toBeInTheDocument();
    expect(screen.queryByTestId("settings-skeleton")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("mounts the Access card for a reverse-proxy account that cannot write", () => {
    // No password session, no `write`: its own two-factor is still how it
    // confirms sensitive changes, so the card must be reachable.
    useAuthStore.setState({
      canWrite: false,
      passwordManagementEnabled: true,
      passwordSessionActive: false,
      user: createSessionUser({ id: "user_viewer", username: "viewer" }),
    });

    renderSettings("/settings/access");

    expect(screen.getByRole("heading", { level: 3, name: "Access" })).toBeInTheDocument();
  });
});
