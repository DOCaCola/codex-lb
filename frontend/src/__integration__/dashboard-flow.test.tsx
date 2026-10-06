import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { BrowserRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import App from "@/App";
import {
  createAccountSummary,
  createDashboardOverview,
  createConversationEntry,
  createConversationsResponse,
  createDefaultRequestLogs,
  createRequestLogEntry,
  createRequestLogFilterOptions,
  createRequestLogsResponse,
} from "@/test/mocks/factories";
import { queryClient } from "@/lib/query-client";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

if (!HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: () => {},
  });
}

const REQUEST_LOG_OUTAGE_MESSAGE = "forced request-log outage";

afterEach(() => {
  queryClient.clear();
});

function overviewForTimeframe(timeframe: string) {
  return createDashboardOverview({
    timeframe:
      timeframe === "1d"
        ? {
            key: "1d",
            windowMinutes: 1440,
            bucketSeconds: 3600,
            bucketCount: 24,
          }
        : timeframe === "30d"
          ? {
              key: "30d",
              windowMinutes: 43200,
              bucketSeconds: 86400,
              bucketCount: 30,
            }
          : {
              key: "7d",
              windowMinutes: 10080,
              bucketSeconds: 21600,
              bucketCount: 28,
            },
  });
}

function logsSection() {
  return within(screen.getByTestId("logs-section"));
}

describe("dashboard flow integration", () => {
  it("loads the dashboard without request logs and refetches the overview on timeframe changes", async () => {
    let overviewCalls = 0;
    let requestLogCalls = 0;
    const overviewTimeframes: string[] = [];

    server.use(
      http.get("/api/dashboard/overview", ({ request }) => {
        overviewCalls += 1;
        const timeframe = new URL(request.url).searchParams.get("timeframe") ?? "7d";
        overviewTimeframes.push(timeframe);
        return HttpResponse.json(overviewForTimeframe(timeframe));
      }),
      http.get("/api/request-logs", () => {
        requestLogCalls += 1;
        return HttpResponse.json(createRequestLogsResponse([], 0, false));
      }),
    );

    window.history.pushState({}, "", "/dashboard");
    renderWithProviders(<App />);

    expect(
      await screen.findByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    await waitFor(() => expect(overviewCalls).toBeGreaterThan(0));
    expect(overviewTimeframes.at(-1)).toBe("7d");
    expect(screen.queryByTestId("logs-section")).not.toBeInTheDocument();

    const overviewAfterLoad = overviewCalls;
    act(() => {
      window.history.pushState({}, "", "/dashboard?overviewTimeframe=30d");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(overviewCalls).toBeGreaterThan(overviewAfterLoad);
    });
    expect(overviewTimeframes.at(-1)).toBe("30d");
    expect(requestLogCalls).toBe(0);
  });

  it("loads the Logs tab and refetches only request logs on filter and page changes", async () => {
    const user = userEvent.setup({ delay: null });
    const logs = createDefaultRequestLogs();

    let overviewCalls = 0;
    let requestLogCalls = 0;

    server.use(
      http.get("/api/dashboard/overview", () => {
        overviewCalls += 1;
        return HttpResponse.json(overviewForTimeframe("7d"));
      }),
      http.get("/api/request-logs", ({ request }) => {
        requestLogCalls += 1;
        const url = new URL(request.url);
        const limit = Number(url.searchParams.get("limit") ?? "25");
        const offset = Number(url.searchParams.get("offset") ?? "0");
        const page = logs.slice(offset, Math.min(logs.length, offset + limit));
        return HttpResponse.json(createRequestLogsResponse(page, 100, true));
      }),
      http.get("/api/request-logs/options", () =>
        HttpResponse.json(createRequestLogFilterOptions()),
      ),
    );

    window.history.pushState({}, "", "/logs");
    renderWithProviders(<App />);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Logs" }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(overviewCalls).toBeGreaterThan(0);
      expect(requestLogCalls).toBeGreaterThan(0);
    });

    const logsAfterLoad = requestLogCalls;
    const overviewAfterLoad = overviewCalls;

    await user.type(
      screen.getByPlaceholderText(
        "Search request id, account, API key, model, error...",
      ),
      "quota",
    );

    await waitFor(() => {
      expect(requestLogCalls).toBeGreaterThan(logsAfterLoad);
    });
    expect(overviewCalls).toBe(overviewAfterLoad);

    const logsAfterFilter = requestLogCalls;
    await user.click(screen.getByRole("button", { name: "Next page" }));

    await waitFor(() => {
      expect(requestLogCalls).toBeGreaterThan(logsAfterFilter);
    });
    expect(overviewCalls).toBe(overviewAfterLoad);
  });

  it("shows an initial request-log failure in the Logs tab and recovers with Retry", async () => {
    const user = userEvent.setup({ delay: null });
    let overviewCalls = 0;
    let requestLogCalls = 0;
    let optionsCalls = 0;
    let requestLogsAvailable = false;
    let releaseRecoveredResponse = () => {};
    const recoveredResponseGate = new Promise<void>((resolve) => {
      releaseRecoveredResponse = resolve;
    });
    const recoveredLog = createRequestLogEntry({
      requestId: "req_recovered",
      accountId: "acc_healthy_overview",
      apiKeyName: "Recovered API Key",
    });

    const overview = createDashboardOverview({
      accounts: [
        createAccountSummary({
          accountId: "acc_healthy_overview",
          email: "healthy-overview@example.com",
          displayName: "Healthy Overview Account",
        }),
      ],
    });

    server.use(
      http.get("/api/dashboard/overview", () => {
        overviewCalls += 1;
        return HttpResponse.json(overview);
      }),
      http.get("/api/request-logs/options", () => {
        optionsCalls += 1;
        return HttpResponse.json(createRequestLogFilterOptions());
      }),
      http.get("/api/request-logs", async () => {
        requestLogCalls += 1;
        if (!requestLogsAvailable) {
          return HttpResponse.json(
            {
              error: {
                code: "forced_request_log_outage",
                message: REQUEST_LOG_OUTAGE_MESSAGE,
              },
            },
            { status: 500 },
          );
        }

        await recoveredResponseGate;
        return HttpResponse.json(
          createRequestLogsResponse([recoveredLog], 1, false),
        );
      }),
    );

    window.history.pushState({}, "", "/logs");
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { level: 1, name: "Logs" }),
    ).toBeInTheDocument();
    const requestLogs = logsSection();
    const errorAlert = await requestLogs.findByRole("alert");

    await waitFor(() => {
      expect(overviewCalls).toBeGreaterThan(0);
      expect(requestLogCalls).toBeGreaterThan(1);
      expect(optionsCalls).toBeGreaterThan(0);
    });

    expect(errorAlert).toHaveTextContent(REQUEST_LOG_OUTAGE_MESSAGE);
    expect(
      requestLogs.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();

    const overviewCallsBeforeRetry = overviewCalls;
    const requestLogCallsBeforeRetry = requestLogCalls;
    const optionsCallsBeforeRetry = optionsCalls;
    const retryButton = requestLogs.getByRole("button", { name: "Retry" });
    requestLogsAvailable = true;

    retryButton.focus();
    expect(retryButton).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(requestLogCalls).toBe(requestLogCallsBeforeRetry + 1);
    });

    expect(overviewCalls).toBe(overviewCallsBeforeRetry);
    expect(optionsCalls).toBe(optionsCallsBeforeRetry);

    releaseRecoveredResponse();
    expect(await screen.findByText("Recovered API Key")).toBeInTheDocument();
    expect(
      screen.queryByText(REQUEST_LOG_OUTAGE_MESSAGE),
    ).not.toBeInTheDocument();
    expect(overviewCalls).toBe(overviewCallsBeforeRetry);
    expect(optionsCalls).toBe(optionsCallsBeforeRetry);
  });

  it("keeps retained request-log rows through failed refresh and Retry recovery", async () => {
    const user = userEvent.setup({ delay: null });
    let requestLogsAvailable = true;
    let recovered = false;
    let requestLogCalls = 0;
    const retainedLog = createRequestLogEntry({
      requestId: "req_retained_refresh",
      apiKeyName: "Retained API Key",
    });
    const recoveredLog = createRequestLogEntry({
      requestId: "req_recovered_refresh",
      apiKeyName: "Recovered API Key",
    });

    server.use(
      http.get("/api/request-logs", () => {
        requestLogCalls += 1;
        if (!requestLogsAvailable) {
          return HttpResponse.json(
            {
              error: {
                code: "forced_background_refresh_failure",
                message: REQUEST_LOG_OUTAGE_MESSAGE,
              },
            },
            { status: 503 },
          );
        }
        return HttpResponse.json(
          createRequestLogsResponse(
            [recovered ? recoveredLog : retainedLog],
            1,
            false,
          ),
        );
      }),
    );

    window.history.pushState({}, "", "/logs");
    const { queryClient: testQueryClient } = renderWithProviders(<App />);

    expect(await screen.findByText("Retained API Key")).toBeInTheDocument();
    const requestLogs = logsSection();
    expect(requestLogs.getByRole("table")).toBeVisible();

    const callsBeforeRefresh = requestLogCalls;
    requestLogsAvailable = false;
    await act(async () => {
      await testQueryClient.invalidateQueries({
        queryKey: ["dashboard", "request-logs"],
      });
    });
    await waitFor(() =>
      expect(requestLogCalls).toBeGreaterThan(callsBeforeRefresh),
    );
    const alert = await requestLogs.findByRole("alert");

    expect(alert).toHaveTextContent(REQUEST_LOG_OUTAGE_MESSAGE);
    expect(requestLogs.getByRole("table")).toBeVisible();
    expect(requestLogs.getByText("Retained API Key")).toBeVisible();

    requestLogsAvailable = true;
    recovered = true;
    const retry = requestLogs.getByRole("button", { name: "Retry" });
    retry.focus();
    await user.keyboard("{Enter}");

    expect(await requestLogs.findByText("Recovered API Key")).toBeVisible();
    expect(requestLogs.queryByText("Retained API Key")).not.toBeInTheDocument();
    expect(requestLogs.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("switches to conversations without reinterpreting request-log URL state", async () => {
    const user = userEvent.setup({ delay: null });
    server.use(
      http.get("/api/conversations", () =>
        HttpResponse.json(
          createConversationsResponse(
            [
              createConversationEntry({
                conversationId: "opencode_conversation",
              }),
            ],
            1,
            false,
          ),
        ),
      ),
    );
    window.history.pushState(
      {},
      "",
      "/logs?search=requestlog&limit=10&offset=25&conversationSearch=opencode&conversationLimit=15&conversationOffset=7",
    );

    renderWithProviders(<App />);

    await user.click(
      await screen.findByRole("button", { name: "Conversations" }),
    );

    expect(
      await screen.findByText("opencode_conversation"),
    ).toBeInTheDocument();
    expect(window.location.search).toContain("view=conversations");
    expect(window.location.search).toContain("search=requestlog");
    expect(window.location.search).toContain("limit=10");
    expect(window.location.search).toContain("offset=25");
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(window.location.search).toContain("conversationSearch=opencode");
    expect(window.location.search).toContain("conversationLimit=15");
    expect(window.location.search).toContain("conversationOffset=7");

    await user.click(screen.getByRole("button", { name: "Request Logs" }));

    await waitFor(() =>
      expect(window.location.search).not.toContain("view=conversations"),
    );
    expect(window.location.search).toContain("search=requestlog");
    expect(window.location.search).toContain("limit=10");
    expect(window.location.search).toContain("offset=25");
    expect(window.location.search).toContain("conversationSearch=opencode");
    expect(window.location.search).toContain("conversationLimit=15");
    expect(window.location.search).toContain("conversationOffset=7");
  });
});
