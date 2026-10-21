import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { cacheBand } from "@/features/dashboard/cache-band";
import { ConversationTrace } from "@/features/dashboard/components/conversation-trace";
import { createConversationTrace, createConversationTraceRequest } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

describe("cacheBand", () => {
  it("uses the high, mid and low cache-read bands", () => {
    expect(cacheBand(0.8)).toBe("high");
    expect(cacheBand(0.3)).toBe("mid");
    expect(cacheBand(0.29)).toBe("low");
    expect(cacheBand(null)).toBe("none");
  });
});

describe("ConversationTrace", () => {
  it("shows cache share, event tags and failures per request", async () => {
    server.use(
      http.get("/api/request-logs/conversation-trace", ({ request }) => {
        expect(new URL(request.url).searchParams.get("conversationId")).toBe("conv_trace");
        return HttpResponse.json(
          createConversationTrace([
            createConversationTraceRequest({ id: 3, latencyMs: 2000 }),
            createConversationTraceRequest({
              id: 2,
              latencyMs: 8000,
              promptTokens: 120_000,
              cacheReadTokens: 0,
              cacheReadRatio: 0,
              cacheEvent: "idle_expiry",
              idleGapMs: 3_900_000,
            }),
            createConversationTraceRequest({
              id: 1,
              status: "error",
              errorCode: "stream_incomplete",
              promptTokens: 0,
              cacheReadTokens: 0,
              cacheReadRatio: null,
            }),
          ]),
        );
      }),
    );
    renderWithProviders(<ConversationTrace conversationId="conv_trace" enabled />);

    const rows = await screen.findAllByTestId("conversation-trace-row");
    expect(rows).toHaveLength(3);
    expect(within(rows[0]).getByText("95% of 100K")).toBeInTheDocument();
    const expiry = within(rows[1]).getByText("idle expiry");
    expect(expiry).toHaveAttribute("title", expect.stringContaining("Idle for"));
    expect(rows[1].querySelector("[data-band]")).toHaveAttribute("data-band", "low");
    expect(rows[1].querySelector<HTMLElement>("[data-band]")?.style.width).toBe("100%");
    expect(within(rows[2]).getByText("stream_incomplete")).toBeInTheDocument();
    expect(rows[2].querySelector("[data-band]")).toHaveAttribute("data-band", "none");
    expect(screen.getByText("3 of 3")).toBeInTheDocument();
  });

  it("loads further pages on request", async () => {
    server.use(
      http.get("/api/request-logs/conversation-trace", ({ request }) => {
        const offset = Number(new URL(request.url).searchParams.get("offset"));
        return HttpResponse.json(
          offset === 0
            ? createConversationTrace([createConversationTraceRequest({ id: 2 })], 2, true)
            : createConversationTrace([createConversationTraceRequest({ id: 1 })], 2, false),
        );
      }),
    );
    renderWithProviders(<ConversationTrace conversationId="conv_pages" enabled />);

    expect(await screen.findAllByTestId("conversation-trace-row")).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findAllByTestId("conversation-trace-row")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });
});

