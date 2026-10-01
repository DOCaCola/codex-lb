import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";
import { ClaudeCacheActivity } from "./claude-cache-activity";

const URL = "/api/request-logs/claude-cache-activity";
const emptyWindow = {
  requests: 0,
  measuredRequests: 0,
  inputTokens: 0,
  cacheReadTokens: 0,
  cacheWriteTokens: 0,
  cacheReadRatio: null,
};

describe("ClaudeCacheActivity", () => {
  const previousPermissions = useAuthStore.getState().permissions;
  beforeEach(() =>
    useAuthStore.setState({ permissions: ["accounts:read:all"] }),
  );
  afterEach(() => useAuthStore.setState({ permissions: previousPermissions }));

  it("compares observations and distinguishes measured zero from missing usage", async () => {
    server.use(
      http.get(URL, () =>
        HttpResponse.json({
          generatedAt: "2026-10-01T10:00:00Z",
          windowMinutes: 60,
          groups: [
            {
              sourceId: "claude-a",
              model: "anthropic/test",
              readRatioChange: -0.8,
              current: {
                ...emptyWindow,
                requests: 3,
                measuredRequests: 1,
                inputTokens: 1000,
                cacheReadRatio: 0,
              },
              previous: {
                ...emptyWindow,
                requests: 1,
                measuredRequests: 1,
                inputTokens: 1000,
                cacheReadTokens: 800,
                cacheReadRatio: 0.8,
              },
            },
            {
              sourceId: "claude-b",
              model: "anthropic/unknown",
              readRatioChange: null,
              current: { ...emptyWindow, requests: 1 },
              previous: emptyWindow,
            },
          ],
        }),
      ),
    );
    renderWithProviders(
      <ClaudeCacheActivity accountLabels={{ "claude-a": "Alpha" }} />,
    );
    const rows = await screen.findAllByRole("row");
    expect(within(rows[1]).getByText("Alpha")).toBeInTheDocument();
    expect(within(rows[1]).getByText("0.0%")).toBeInTheDocument();
    expect(within(rows[1]).getByText("80.0%")).toBeInTheDocument();
    expect(within(rows[1]).getByText("1 / 3")).toBeInTheDocument();
    expect(within(rows[2]).getAllByText("—")).toHaveLength(3);
    expect(
      screen.getByText(/missing usage is not a cache miss/),
    ).toBeInTheDocument();
  });

  it("shows failure and permits explicit retry", async () => {
    let attempts = 0;
    server.use(
      http.get(URL, () => {
        attempts++;
        return attempts === 1
          ? HttpResponse.json(
              {
                error: {
                  code: "unavailable",
                  message: "Cache query unavailable",
                },
              },
              { status: 503 },
            )
          : HttpResponse.json({
              generatedAt: "2026-10-01T10:00:00Z",
              windowMinutes: 60,
              groups: [],
            });
      }),
    );
    renderWithProviders(<ClaudeCacheActivity accountLabels={{}} />);
    expect(
      await screen.findByText("Cache query unavailable"),
    ).toBeInTheDocument();
    expect(attempts).toBe(1);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(/No successful Claude/)).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it("does not fetch without account-read permission", async () => {
    useAuthStore.setState({ permissions: [] });
    const calls = vi.fn();
    server.use(
      http.get(URL, () => {
        calls();
        return HttpResponse.json({});
      }),
    );
    const { container } = renderWithProviders(
      <ClaudeCacheActivity accountLabels={{}} />,
    );
    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(calls).not.toHaveBeenCalled();
  });
});
