import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/mocks/server";
import { ClaudeResetGrants } from "./reset-grants";

const grant = {
  id: "grant",
  label: "Claude launch reset",
  resets_total: 1,
  resets_left: 1,
  clears: ["five_hour", "seven_day"],
  starts_at: null,
  ends_at: null,
  paused: false,
  usable_now: true,
  use_requires_limit: true,
};
const status = {
  eligible: true,
  at_limit: true,
  ineligible_reason: null,
  cooldown_until: null,
  grants: [grant],
};

function show(readOnly = false) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ClaudeResetGrants accountId="test" readOnly={readOnly} />
    </QueryClientProvider>,
  );
}

describe("Claude reset grants", () => {
  it("requires explicit confirmation and recovers the same operation", async () => {
    const bodies: {
      grantId: string;
      operationId: string;
      confirmed: boolean;
    }[] = [];
    let operations: unknown[] = [];
    server.use(
      http.get("/api/claude-accounts/test/reset-grants", () =>
        HttpResponse.json({ status, operations, error: null }),
      ),
      http.post(
        "/api/claude-accounts/test/reset-grants/consume",
        async ({ request }) => {
          const body = (await request.json()) as (typeof bodies)[number];
          bodies.push(body);
          const operation = {
            operationId: body.operationId,
            grantId: body.grantId,
            createdAt: new Date().toISOString(),
            leaseUntil: new Date(0).toISOString(),
            retryUntil: new Date(Date.now() + 600000).toISOString(),
            result:
              bodies.length === 1
                ? null
                : { result: "reset", resets_left: 0, cleared: ["five_hour"] },
          };
          operations = [operation];
          return HttpResponse.json({ operation, refreshComplete: false });
        },
      ),
    );
    vi.spyOn(crypto, "randomUUID").mockReturnValue(
      "994a041f-0104-4858-89eb-57e46f6af8b4",
    );
    show();
    await userEvent.click(screen.getByRole("button", { name: "Reset grants" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Redeem grant" }),
    );
    expect(bodies).toHaveLength(0);
    await userEvent.click(
      screen.getByRole("button", { name: "Confirm redemption" }),
    );
    const retry = await screen.findByRole("button", {
      name: "Retry same operation",
    });
    await waitFor(() => expect(retry).toBeEnabled());
    await userEvent.click(retry);
    await screen.findByText(
      /Redemption is confirmed; usage refresh is pending/,
    );
    expect(bodies).toHaveLength(2);
    expect(bodies[0].operationId).toBe(bodies[1].operationId);
    expect(bodies[0].confirmed).toBe(true);
  });

  it("lets read-only users inspect but not spend", async () => {
    server.use(
      http.get("/api/claude-accounts/test/reset-grants", () =>
        HttpResponse.json({ status, operations: [], error: null }),
      ),
    );
    show(true);
    await userEvent.click(screen.getByRole("button", { name: "Reset grants" }));
    expect(
      await screen.findByRole("button", { name: "Redeem grant" }),
    ).toBeDisabled();
  });

  it("keeps expired uncertainty visible and requires separate risk acknowledgement", async () => {
    server.use(
      http.get("/api/claude-accounts/test/reset-grants", () =>
        HttpResponse.json({
          status,
          error: null,
          operations: [
            {
              operationId: "old",
              grantId: "grant",
              createdAt: new Date(0).toISOString(),
              retryUntil: new Date(0).toISOString(),
              leaseUntil: new Date(0).toISOString(),
              result: null,
            },
          ],
        }),
      ),
    );
    show();
    await userEvent.click(screen.getByRole("button", { name: "Reset grants" }));
    expect(
      await screen.findByRole("button", { name: "Redeem grant" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Retry same operation" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: "Redeem grant" })).toBeEnabled();
  });
});
