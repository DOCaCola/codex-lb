import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/utils";
import {
  ADMIN_PERMISSIONS,
  OPERATOR_PERMISSIONS,
  VIEWER_PERMISSIONS,
  createDashboardOverview,
  createRequestLogEntry,
} from "@/test/mocks/factories";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { useDashboard } from "@/features/dashboard/hooks/use-dashboard";
import { useRequestLogs } from "@/features/dashboard/hooks/use-request-logs";
import { useConversations } from "@/features/dashboard/hooks/use-conversations";
import { REQUEST_LOG_TABLE_PREFERENCES_STORAGE_KEY } from "@/features/dashboard/hooks/use-request-log-table-preferences";
import { parseConversationTimeframe } from "@/features/dashboard/schemas";
import type { RecentRequestsTableProps } from "@/features/dashboard/components/recent-requests-table";

import { LogsPage } from "./logs-page";

const { conversationsViewSpy, recentRequestsTableSpy } = vi.hoisted(() => ({
  conversationsViewSpy: vi.fn(),
  recentRequestsTableSpy: vi.fn(),
}));

vi.mock("@/features/dashboard/hooks/use-dashboard", () => ({
  useDashboard: vi.fn(),
}));

vi.mock("@/features/dashboard/hooks/use-request-logs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/dashboard/hooks/use-request-logs")>();
  return {
    ...actual,
    useRequestLogs: vi.fn(),
  };
});

vi.mock("@/features/dashboard/hooks/use-conversations", () => ({
  useConversations: vi.fn(),
}));

vi.mock("@/features/dashboard/components/conversations-view", () => ({
  ConversationsView: (props: { state?: ReturnType<typeof useConversations>; accounts?: unknown[] }) => {
    conversationsViewSpy(props);
    return <div data-testid="conversations-view" />;
  },
}));

vi.mock("@/features/dashboard/components/filters/conversation-timeframe-select", () => ({
  ConversationTimeframeSelect: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (value: "30d") => void;
  }) => (
    <button type="button" data-testid="conversation-timeframe-select" onClick={() => onChange("30d")}>
      {value}
    </button>
  ),
}));

vi.mock("@/features/dashboard/components/recent-requests-table", () => ({
  RecentRequestsTable: (props: RecentRequestsTableProps) => {
    recentRequestsTableSpy(props);
    return <div data-testid="recent-requests-table" />;
  },
}));

const useDashboardMock = vi.mocked(useDashboard);
const useRequestLogsMock = vi.mocked(useRequestLogs);
const useConversationsMock = vi.mocked(useConversations);

type RequestLogsQueryOverrides = {
  data?: {
    requests: ReturnType<typeof createRequestLogEntry>[];
    total: number;
    hasMore: boolean;
    costCoverage?: {
      knownCostUsd: number;
      pricedRequests: number;
      unpricedRequests: number;
      unmeteredRequests: number;
      coverageUnknown: boolean;
    };
  };
  error?: Error | null;
  isFetching?: boolean;
  isLoading?: boolean;
  isPending?: boolean;
  isSuccess?: boolean;
};

type ConversationsQueryOverrides = {
  isFetching?: boolean;
};

function logSection() {
  return screen.getByTestId("logs-section");
}

describe("LogsPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      role: "admin",
      permissions: ADMIN_PERMISSIONS,
      canWrite: true,
      initialized: true,
    });
    conversationsViewSpy.mockReset();
    recentRequestsTableSpy.mockReset();
    useDashboardMock.mockReset();
    useRequestLogsMock.mockReset();
    useConversationsMock.mockReset();
    window.localStorage.removeItem(REQUEST_LOG_TABLE_PREFERENCES_STORAGE_KEY);
  });

  function mockReadyLogs(
    logsQueryOverrides: RequestLogsQueryOverrides = {},
    optionsError: Error | null = null,
    conversationsQueryOverrides: ConversationsQueryOverrides = {},
  ) {
    const overview = createDashboardOverview();
    useDashboardMock.mockReturnValue({
      data: overview,
      isFetching: false,
      error: null,
    } as ReturnType<typeof useDashboard>);
    useRequestLogsMock.mockReturnValue({
      filters: {
        search: "",
        timeframe: "all",
        accountIds: [],
        apiKeyIds: [],
        modelOptions: [],
        statuses: [],
        limit: 25,
        offset: 0,
      },
      listFilters: {
        search: undefined,
        limit: 25,
        offset: 0,
        accountIds: [],
        apiKeyIds: [],
        statuses: [],
        modelOptions: [],
        since: undefined,
      },
      facetFilters: {
        since: undefined,
        accountIds: [],
        apiKeyIds: [],
        modelOptions: [],
      },
      logsQuery: {
        data: { requests: [], total: 0, hasMore: false },
        isFetching: false,
        error: null,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        refetch: vi.fn(),
        ...logsQueryOverrides,
      },
      optionsQuery: {
        data: { accountIds: [], apiKeys: [], modelOptions: [], statuses: [] },
        error: optionsError,
      },
      updateFilters: vi.fn(),
    } as unknown as ReturnType<typeof useRequestLogs>);
    useConversationsMock.mockReturnValue({
      filters: {
        search: "",
        limit: 25,
        offset: 0,
        timeframe: parseConversationTimeframe(
          new URLSearchParams(window.location.search).get("conversationTimeframe"),
        ),
      },
      listFilters: { limit: 25, offset: 0 },
      conversationsQuery: {
        data: { conversations: [], total: 0, hasMore: false },
        error: null,
        isFetching: conversationsQueryOverrides.isFetching ?? false,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        refetch: vi.fn(),
      },
      updateFilters: vi.fn(),
    } as unknown as ReturnType<typeof useConversations>);

    return overview;
  }

  it("renders request-log loading inside the logs section", () => {
    mockReadyLogs({
      data: undefined,
      error: null,
      isFetching: true,
      isLoading: true,
      isPending: true,
      isSuccess: false,
    });

    renderWithProviders(<LogsPage />);

    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Log controls" })).toBeInTheDocument();
    expect(within(logSection()).getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByTestId("recent-requests-table")).not.toBeInTheDocument();
    expect(screen.queryByTestId("compact-pagination")).not.toBeInTheDocument();
  });

  it("surfaces request-log option errors only while Request Logs is active", () => {
    const optionsError = new Error("request-log options unavailable");
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs({}, optionsError);

    renderWithProviders(<LogsPage />);

    expect(screen.queryByText(optionsError.message)).not.toBeInTheDocument();
  });

  it("surfaces active request-log option errors", () => {
    const optionsError = new Error("request-log options unavailable");
    window.history.pushState({}, "", "/logs");
    mockReadyLogs({}, optionsError);

    renderWithProviders(<LogsPage />);

    expect(screen.getByText(optionsError.message)).toBeInTheDocument();
  });

  it("uses the active conversation query for refresh state", () => {
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs({ isFetching: true }, null, { isFetching: false });

    renderWithProviders(<LogsPage />);

    const refreshButton = screen.getByRole("button", { name: "Refresh logs" });
    expect(refreshButton).not.toBeDisabled();
    expect(refreshButton.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("disables refresh while the active conversation query is fetching", () => {
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs({ isFetching: false }, null, { isFetching: true });

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("button", { name: "Refresh logs" })).toBeDisabled();
  });

  it("passes the single conversation observer and overview accounts into the conversations view", () => {
    window.history.pushState({}, "", "/logs?view=conversations");
    const overview = mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(useConversationsMock).toHaveBeenCalledTimes(1);
    expect(conversationsViewSpy).toHaveBeenCalledTimes(1);
    expect(conversationsViewSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        state: expect.objectContaining({ conversationsQuery: expect.any(Object) }),
        accounts: overview.accounts,
      }),
    );
  });

  it("switches between request logs and conversations with a segmented view toggle", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    const viewToggle = within(screen.getByRole("group", { name: "Log view" }));
    expect(viewToggle.getByRole("button", { name: "Conversations" })).toHaveAttribute("aria-pressed", "true");
    expect(viewToggle.getByRole("button", { name: "Request Logs" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("conversations-view")).toBeInTheDocument();

    await user.click(viewToggle.getByRole("button", { name: "Request Logs" }));

    expect(viewToggle.getByRole("button", { name: "Request Logs" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
    expect(screen.getByTestId("recent-requests-table")).toBeInTheDocument();
    expect(window.location.search).not.toContain("view=conversations");
  });

  it("renders the conversation timeframe selector only for Conversations and resets its offset", () => {
    window.history.pushState({}, "", "/logs?view=conversations&conversationOffset=25");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByTestId("conversation-timeframe-select")).toHaveTextContent("7d");

    fireEvent.click(screen.getByTestId("conversation-timeframe-select"));

    expect(useConversationsMock.mock.results[0]?.value.updateFilters).toHaveBeenCalledWith(
      {
        timeframe: "30d",
        offset: 0,
      },
    );
  });

  it("restores the retained conversation timeframe after switching views", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/logs?view=conversations&conversationTimeframe=30d");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByTestId("conversation-timeframe-select")).toHaveTextContent("30d");
    await user.click(screen.getByRole("button", { name: "Request Logs" }));
    expect(screen.queryByTestId("conversation-timeframe-select")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Conversations" }));

    expect(screen.getByTestId("conversation-timeframe-select")).toHaveTextContent("30d");
  });

  it("hides Conversations and normalizes guest deep links", async () => {
    useAuthStore.setState({
      role: "guest",
      permissions: ["read"],
      canWrite: false,
    });
    window.history.pushState({}, "", "/logs?view=conversations");
    const historyLength = window.history.length;
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("heading", { name: "Request Logs" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Log view" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conversations" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
    expect(screen.queryByTestId("conversation-timeframe-select")).not.toBeInTheDocument();
    expect(useConversationsMock.mock.calls.every(([options]) => options !== undefined && options.enabled === false)).toBe(true);
    await waitFor(() => {
      expect(window.location.search).not.toContain("view=conversations");
      expect(window.history.length).toBe(historyLength);
    });
  });

  it.each([
    ["an operator", OPERATOR_PERMISSIONS, true],
    ["a viewer", VIEWER_PERMISSIONS, false],
  ])("hides Conversations from %s (no conversations:read) even though the wire role is admin", async (_label, permissions, canWrite) => {
    useAuthStore.setState({ role: "admin", permissions, canWrite });
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("heading", { name: "Request Logs" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conversations" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
    expect(useConversationsMock.mock.calls.every(([options]) => options !== undefined && options.enabled === false)).toBe(true);
    await waitFor(() => expect(window.location.search).not.toContain("view=conversations"));
  });

  it("fails closed during auth hydration and preserves an admin bookmark until the guest is known", async () => {
    useAuthStore.setState({
      initialized: false,
      role: "admin",
      permissions: ADMIN_PERMISSIONS,
      canWrite: true,
    });
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("heading", { name: "Request Logs" })).toBeInTheDocument();
    expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
    expect(window.location.search).toContain("view=conversations");
    expect(useConversationsMock.mock.calls.every(([options]) => options !== undefined && options.enabled === false)).toBe(true);

    act(() => {
      useAuthStore.setState({
        initialized: true,
        role: "guest",
        permissions: ["read"],
        canWrite: false,
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Request Logs" })).toBeInTheDocument();
      expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
      expect(window.location.search).not.toContain("view=conversations");
    });
    expect(useConversationsMock.mock.calls.every(([options]) => options !== undefined && options.enabled === false)).toBe(true);
  });

  it("fails closed during auth hydration from the least-privilege boot state", async () => {
    // The store now boots as guest with no permissions; the gate normally
    // holds rendering until initialized, but the page must still fail closed
    // if it is mounted before the session resolves.
    useAuthStore.setState({
      initialized: false,
      role: "guest",
      permissions: [],
      canWrite: false,
    });
    window.history.pushState({}, "", "/logs?view=conversations");
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("heading", { name: "Request Logs" })).toBeInTheDocument();
    expect(screen.queryByTestId("conversations-view")).not.toBeInTheDocument();
    expect(window.location.search).toContain("view=conversations");
    expect(useConversationsMock.mock.calls.every(([options]) => options !== undefined && options.enabled === false)).toBe(true);

    act(() => {
      useAuthStore.setState({
        initialized: true,
        role: "admin",
        permissions: ADMIN_PERMISSIONS,
        canWrite: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("conversations-view")).toBeInTheDocument();
    });
    expect(window.location.search).toContain("view=conversations");
  });

  it("customizes and restores the request-log table without a global width control", async () => {
    const user = userEvent.setup();
    mockReadyLogs();

    renderWithProviders(<LogsPage />);

    expect(screen.getByRole("button", { name: "Columns (12)" })).toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.queryByText(/^Width$/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Columns (12)" }));
    expect(screen.getByText("Visible columns")).toBeInTheDocument();
    await user.click(screen.getByRole("menuitemcheckbox", { name: "Plan" }));

    expect(screen.getByRole("menu", { name: "Columns (11)" })).toBeInTheDocument();
    const selectedProps = recentRequestsTableSpy.mock.lastCall?.[0] as
      | RecentRequestsTableProps
      | undefined;
    expect(selectedProps?.visibleColumns).not.toContain("plan");

    act(() => {
      selectedProps?.onColumnWidthChange?.("account", 240);
    });
    const resizedProps = recentRequestsTableSpy.mock.lastCall?.[0] as
      | RecentRequestsTableProps
      | undefined;
    expect(resizedProps?.columnWidths?.account).toBe(240);

    await user.keyboard("{Escape}");
    await user.click(
      screen.getByRole("button", { name: "Restore default column layout" }),
    );

    const restoredProps = recentRequestsTableSpy.mock.lastCall?.[0] as
      | RecentRequestsTableProps
      | undefined;
    expect(restoredProps?.visibleColumns).toHaveLength(12);
    expect(restoredProps?.columnWidths).toEqual({});
    expect(
      window.localStorage.getItem(REQUEST_LOG_TABLE_PREFERENCES_STORAGE_KEY),
    ).toBeNull();
  });

  it("renders conversation badge between Statuses and Reset in filters", () => {
    mockReadyLogs();
    const updateFilters = vi.fn();
    useRequestLogsMock.mockReturnValue({
      filters: {
        search: "",
        timeframe: "all",
        accountIds: [],
        apiKeyIds: [],
        modelOptions: [],
        statuses: ["ok"],
        conversationId: "conv_page_badge",
        limit: 25,
        offset: 0,
      },
      listFilters: { search: undefined, limit: 25, offset: 0, accountIds: [], apiKeyIds: [], statuses: ["ok"], modelOptions: [], since: undefined },
      facetFilters: { since: undefined, accountIds: [], apiKeyIds: [], modelOptions: [] },
      logsQuery: {
        data: { requests: [], total: 0, hasMore: false },
        isFetching: false,
        error: null,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        refetch: vi.fn(),
      },
      optionsQuery: {
        data: { accountIds: [], apiKeys: [], modelOptions: [], statuses: ["ok", "error"] },
        error: null,
      },
      updateFilters,
    } as unknown as ReturnType<typeof useRequestLogs>);


    renderWithProviders(<LogsPage />);

    // Badge text appears with the conversation ID
    expect(screen.getByText(/conv_page_badge/)).toBeInTheDocument();
    // Reset button exists
    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
    // Dismiss button exists
    expect(screen.getByRole("button", { name: /remove conversation/i })).toBeInTheDocument();
  });

  it("summarizes the filtered requests and their cost in the toolbar", () => {
    mockReadyLogs({
      data: {
        requests: [],
        total: 1234,
        hasMore: true,
        costCoverage: {
          knownCostUsd: 3.14,
          pricedRequests: 1234,
          unpricedRequests: 0,
          unmeteredRequests: 0,
          coverageUnknown: false,
        },
      },
    });

    renderWithProviders(<LogsPage />);

    expect(screen.getByTestId("logs-summary")).toHaveTextContent("1,234 requests · $3.14");
    expect(screen.queryByText(/The conversation/)).not.toBeInTheDocument();
  });

  it("keeps an incomplete cost short and explains its coverage on hover", () => {
    mockReadyLogs({
      data: {
        requests: [],
        total: 42,
        hasMore: true,
        costCoverage: {
          knownCostUsd: 3.14,
          pricedRequests: 40,
          unpricedRequests: 2,
          unmeteredRequests: 0,
          coverageUnknown: false,
        },
      },
    });

    renderWithProviders(<LogsPage />);

    const summary = screen.getByTestId("logs-summary");
    expect(summary).toHaveTextContent("42 requests · $3.14");
    expect(summary.firstElementChild).toHaveAttribute(
      "title",
      "$3.14 known · incomplete (40 priced, 2 unpriced)",
    );
  });

  it("pages request logs from the toolbar pager", async () => {
    const user = userEvent.setup();
    mockReadyLogs({ data: { requests: [createRequestLogEntry()], total: 60, hasMore: true } });

    renderWithProviders(<LogsPage />);

    const pager = within(screen.getByTestId("compact-pagination"));
    expect(pager.getByText("1–25 of 60")).toBeInTheDocument();
    expect(pager.getByRole("button", { name: "Previous page" })).toBeDisabled();
    await user.click(pager.getByRole("button", { name: "Next page" }));

    expect(useRequestLogsMock.mock.results[0]?.value.updateFilters).toHaveBeenCalledWith({ offset: 25 });
  });

  it("passes a page key that changes with the query and offset", () => {
    mockReadyLogs({ data: { requests: [], total: 60, hasMore: true } });

    renderWithProviders(<LogsPage />);

    const props = recentRequestsTableSpy.mock.calls.at(-1)?.[0] as RecentRequestsTableProps;
    expect(JSON.parse(props.scrollKey)).toMatchObject({ offset: 0, limit: 25, timeframe: "all" });
  });

  it("dismiss button clears conversationId and resets offset, preserving other filters", () => {
    mockReadyLogs();
    const updateFilters = vi.fn();

    useRequestLogsMock.mockReturnValue({
      filters: {
        search: "test",
        timeframe: "7d",
        accountIds: ["acc_primary"],
        apiKeyIds: [],
        modelOptions: [],
        statuses: ["ok"],
        conversationId: "conv_dismiss_preserve",
        limit: 25,
        offset: 0,
      },
      listFilters: { search: "test", limit: 25, offset: 0, accountIds: ["acc_primary"], apiKeyIds: [], statuses: ["ok"], modelOptions: [], since: expect.any(String) as string },
      facetFilters: { since: expect.any(String) as string, accountIds: ["acc_primary"], apiKeyIds: [], modelOptions: [] },
      logsQuery: {
        data: {
          requests: [],
          total: 0,
          hasMore: false,
        },
        isFetching: false,
        error: null,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        refetch: vi.fn(),
      },
      optionsQuery: {
        data: { accountIds: ["acc_primary"], apiKeys: [], modelOptions: [], statuses: ["ok"] },
        error: null,
      },
      updateFilters,
    } as unknown as ReturnType<typeof useRequestLogs>);


    renderWithProviders(<LogsPage />);

    const dismissButton = screen.getByRole("button", { name: /remove conversation/i });
    fireEvent.click(dismissButton);

    // Should call updateFilters with conversationId:null and offset:0 only
    expect(updateFilters).toHaveBeenCalledWith({ conversationId: null, offset: 0 });
  });

  it("Reset button clears conversation plus all filters", () => {
    mockReadyLogs();
    const updateFilters = vi.fn();

    useRequestLogsMock.mockReturnValue({
      filters: {
        search: "test",
        timeframe: "7d",
        accountIds: ["acc_primary"],
        apiKeyIds: ["key_1"],
        modelOptions: ["gpt-5.1:::high"],
        statuses: ["ok"],
        conversationId: "conv_reset_all",
        limit: 25,
        offset: 5,
      },
      listFilters: { search: "test", limit: 25, offset: 5, accountIds: ["acc_primary"], apiKeyIds: ["key_1"], statuses: ["ok"], modelOptions: ["gpt-5.1:::high"], since: expect.any(String) as string },
      facetFilters: { since: expect.any(String) as string, accountIds: ["acc_primary"], apiKeyIds: ["key_1"], modelOptions: ["gpt-5.1:::high"] },
      logsQuery: {
        data: {
          requests: [],
          total: 0,
          hasMore: false,
        },
        isFetching: false,
        error: null,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        refetch: vi.fn(),
      },
      optionsQuery: {
        data: { accountIds: ["acc_primary"], apiKeys: [{ id: "key_1", name: "Primary Key" }], modelOptions: [{ model: "gpt-5.1", reasoningEffort: "high" }], statuses: ["ok"] },
        error: null,
      },
      updateFilters,
    } as unknown as ReturnType<typeof useRequestLogs>);


    renderWithProviders(<LogsPage />);

    const resetButton = screen.getByRole("button", { name: /reset/i });
    fireEvent.click(resetButton);

    expect(updateFilters).toHaveBeenCalledWith({
      search: "",
      timeframe: "all",
      accountIds: [],
      apiKeyIds: [],
      modelOptions: [],
      statuses: [],
      conversationId: null,
      offset: 0,
    });
  });
});
