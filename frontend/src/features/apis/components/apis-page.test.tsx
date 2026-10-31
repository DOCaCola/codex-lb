import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { ADMIN_PERMISSIONS, createApiKey } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

import { ApisPage } from "./apis-page";

const hookMocks = vi.hoisted(() => ({
  useApiKeys: vi.fn(),
  useApiKeyTrends: vi.fn(),
  useApiKeysTrends: vi.fn(),
  useApiKeyUsage7Day: vi.fn(),
}));

vi.mock("@/features/apis/hooks/use-apis", () => hookMocks);

type MutationMock = {
  isPending: boolean;
  error: Error | null;
  mutateAsync: ReturnType<typeof vi.fn>;
};

type QueryMock<T> = {
  data: T | undefined;
  error: Error | null;
  isPending: boolean;
  isFetching: boolean;
  refetch: ReturnType<typeof vi.fn>;
};

type ApiKeyFixture = ReturnType<typeof createApiKey>;

function createMutationMock(): MutationMock {
  return { isPending: false, error: null, mutateAsync: vi.fn().mockResolvedValue(undefined) };
}

function createQueryMock<T>(data: T | undefined): QueryMock<T> {
  return { data, error: null, isPending: false, isFetching: false, refetch: vi.fn() };
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

function renderApisPage({
  path = "/keys",
  apiKeys = [createApiKey()],
  apiKeysQuery = createQueryMock(apiKeys),
  createMutation = createMutationMock(),
  updateMutation = createMutationMock(),
  deleteMutation = createMutationMock(),
  regenerateMutation = createMutationMock(),
}: {
  path?: string;
  apiKeys?: ApiKeyFixture[];
  apiKeysQuery?: QueryMock<ApiKeyFixture[]>;
  createMutation?: MutationMock;
  updateMutation?: MutationMock;
  deleteMutation?: MutationMock;
  regenerateMutation?: MutationMock;
} = {}) {
  hookMocks.useApiKeys.mockReturnValue({
    apiKeysQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    regenerateMutation,
  });
  hookMocks.useApiKeyTrends.mockReturnValue(createQueryMock(null));
  hookMocks.useApiKeysTrends.mockReturnValue(
    createQueryMock({ series: [], since: "2026-09-23T00:00:00Z", until: "2026-09-30T00:00:00Z" }),
  );
  hookMocks.useApiKeyUsage7Day.mockReturnValue(createQueryMock(null));

  window.history.pushState({}, "", path);
  return renderWithProviders(
    <>
      <Routes>
        <Route path="/keys" element={<ApisPage />} />
        <Route path="/keys/:keyId" element={<ApisPage />} />
        <Route path="/keys/:keyId/settings" element={<ApisPage />} />
        <Route path="*" element={null} />
      </Routes>
      <LocationProbe />
    </>,
  );
}

function twoKeys(): ApiKeyFixture[] {
  return [
    createApiKey({ name: "Primary key" }),
    createApiKey({ id: "key_2", name: "Secondary key", keyPrefix: "sk-secondary", isActive: false }),
  ];
}

// The store boots least-privilege, so every page test that exercises admin
// controls must seed write access explicitly rather than rely on defaults.
beforeEach(() => {
  useAuthStore.setState({ role: "admin", permissions: ADMIN_PERMISSIONS, canWrite: true, initialized: true });
});

afterEach(() => {
  vi.clearAllMocks();
  window.history.pushState({}, "", "/");
});

describe("ApisPage list", () => {
  it("shows the comparison trend above a table of every key", () => {
    renderApisPage({ apiKeys: twoKeys() });

    expect(screen.getByRole("heading", { name: "API Keys" })).toBeInTheDocument();
    expect(screen.getByTestId("api-keys-summary")).toHaveTextContent("2 keys · 1 active");
    const rows = screen.getAllByTestId("api-key-row");
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("Primary key")).toBeInTheDocument();
    const trend = screen.getByTestId("api-keys-comparison-trend");
    expect(trend.compareDocumentPosition(screen.getByTestId("api-keys-list"))).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("filters the table by key status", async () => {
    const user = userEvent.setup();
    renderApisPage({ apiKeys: twoKeys() });

    await user.click(within(screen.getByRole("group", { name: "Key status" })).getByRole("button", { name: /Disabled & expired/ }));

    const rows = screen.getAllByTestId("api-key-row");
    expect(rows).toHaveLength(1);
    expect(within(rows[0]).getByText("Secondary key")).toBeInTheDocument();
  });

  it("opens a key when its row is clicked", async () => {
    const user = userEvent.setup();
    renderApisPage({ apiKeys: twoKeys() });

    await user.click(within(screen.getAllByTestId("api-key-row")[1]).getByText("Secondary key"));

    expect(screen.getByTestId("location")).toHaveTextContent("/keys/key_2");
    expect(screen.getByRole("heading", { name: "Secondary key" })).toBeInTheDocument();
  });

  it("enables a disabled key from its row menu", async () => {
    const user = userEvent.setup();
    const updateMutation = createMutationMock();
    renderApisPage({ apiKeys: twoKeys(), updateMutation });

    await user.click(screen.getByRole("button", { name: "Actions for Secondary key" }));
    await user.click(await screen.findByRole("menuitem", { name: "Enable" }));

    expect(updateMutation.mutateAsync).toHaveBeenCalledWith({ keyId: "key_2", payload: { isActive: true } });
  });

  it("keeps the create dialog open when creation fails", async () => {
    const user = userEvent.setup();
    const createMutation = createMutationMock();
    createMutation.mutateAsync.mockRejectedValue(new Error("boom create"));
    renderApisPage({ createMutation });

    await user.click(screen.getByRole("button", { name: "Create API Key" }));
    const dialog = await screen.findByRole("dialog", { name: "Create API key" });
    await user.type(within(dialog).getByLabelText("Name"), "Broken key");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));

    await waitFor(() => expect(createMutation.mutateAsync).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("dialog", { name: "Create API key" })).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Broken key");
  });

  it("shows a retry state when the initial API key query fails", async () => {
    const user = userEvent.setup();
    const apiKeysQuery = createQueryMock<ApiKeyFixture[]>(undefined);
    apiKeysQuery.error = new Error("boom list");
    renderApisPage({ apiKeys: [], apiKeysQuery });

    expect(screen.getByText("boom list")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(apiKeysQuery.refetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("api-keys-list")).not.toBeInTheDocument();
  });

  it("describes setup when there are no keys yet", () => {
    renderApisPage({ apiKeys: [] });

    expect(screen.getByText("No API keys yet")).toBeInTheDocument();
  });
});

describe("ApisPage key", () => {
  it("shows the key overview next to the key rail", () => {
    renderApisPage({ path: "/keys/key_2", apiKeys: twoKeys() });

    expect(screen.getByTestId("api-key-rail")).toBeInTheDocument();
    expect(screen.getByTestId("api-key-detail")).toHaveAttribute("data-tab", "overview");
    expect(screen.getByRole("heading", { name: "Secondary key" })).toBeInTheDocument();
    expect(screen.getByText("This key is disabled. Requests with it are refused.")).toBeInTheDocument();
    expect(hookMocks.useApiKeyTrends).toHaveBeenCalledWith("key_2", { enabled: true });
  });

  it("switches to the Settings tab in the URL", async () => {
    const user = userEvent.setup();
    renderApisPage({ path: "/keys/key_1", apiKeys: twoKeys() });

    await user.click(within(screen.getByRole("group", { name: "Key view" })).getByRole("button", { name: /settings/i }));

    expect(screen.getByTestId("location")).toHaveTextContent("/keys/key_1/settings");
    expect(screen.getByTestId("api-key-settings")).toBeInTheDocument();
  });

  it("keeps the edits when saving settings fails", async () => {
    const user = userEvent.setup();
    const updateMutation = createMutationMock();
    updateMutation.mutateAsync.mockRejectedValue(new Error("boom update"));
    renderApisPage({ path: "/keys/key_1/settings", updateMutation });

    const nameInput = screen.getByLabelText("Name");
    await user.clear(nameInput);
    await user.type(nameInput, "Renamed key");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(updateMutation.mutateAsync).toHaveBeenCalledWith({ keyId: "key_1", payload: { name: "Renamed key" } }),
    );
    expect(screen.getByLabelText("Name")).toHaveValue("Renamed key");
  });

  it("returns to the list after deleting the open key", async () => {
    const user = userEvent.setup();
    const deleteMutation = createMutationMock();
    renderApisPage({ path: "/keys/key_1/settings", deleteMutation });

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent(/^\/keys$/));
    expect(deleteMutation.mutateAsync).toHaveBeenCalledWith("key_1");
  });

  it("explains an unknown key", () => {
    renderApisPage({ path: "/keys/missing" });

    const notFound = screen.getByTestId("api-key-not-found");
    expect(notFound).toHaveTextContent("API key not found");
    expect(within(notFound).getByRole("link", { name: "All keys" })).toHaveAttribute("href", "/keys");
  });
});

describe("ApisPage permissions", () => {
  it("shows an administrator-only notice and keeps API key queries idle for read-only guests", () => {
    useAuthStore.setState({ role: "guest", permissions: ["read"], canWrite: false, initialized: true });
    renderApisPage({ path: "/keys/key_1" });

    expect(screen.getByRole("heading", { name: "API Keys" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("API keys are managed by administrators");
    expect(hookMocks.useApiKeys).toHaveBeenCalledWith({ enabled: false });
    // Even with a (stale) cached key list, per-key queries stay idle.
    expect(hookMocks.useApiKeyTrends).toHaveBeenCalledWith("key_1", { enabled: false });
    expect(hookMocks.useApiKeyUsage7Day).toHaveBeenCalledWith("key_1", { enabled: false });
    expect(screen.queryByTestId("api-key-detail")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create API Key" })).not.toBeInTheDocument();
  });

  it("lists keys without write controls for api_keys:read without the write alias", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({
      role: "admin",
      permissions: ["read", "api_keys:read:all", "dashboard:read:all"],
      canWrite: false,
      initialized: true,
    });
    renderApisPage();

    expect(hookMocks.useApiKeys).toHaveBeenCalledWith({ enabled: true });
    expect(screen.getByTestId("api-keys-list")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create API Key" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Actions for/ }));
    expect(screen.queryByRole("menuitem", { name: "Regenerate" })).not.toBeInTheDocument();
  });

  it("shows no Settings tab to read-only sessions", () => {
    useAuthStore.setState({
      role: "admin",
      permissions: ["read", "api_keys:read:all", "dashboard:read:all"],
      canWrite: false,
      initialized: true,
    });
    renderApisPage({ path: "/keys/key_1/settings" });

    expect(screen.getByTestId("api-key-detail")).toHaveAttribute("data-tab", "overview");
    expect(screen.queryByRole("group", { name: "Key view" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("api-key-settings")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Regenerate" })).not.toBeInTheDocument();
  });
});
