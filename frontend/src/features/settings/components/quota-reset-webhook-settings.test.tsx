import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { QuotaResetWebhookSettings } from "./quota-reset-webhook-settings";
import { renderWithProviders } from "@/test/utils";
import { server } from "@/test/mocks/server";

const path = "/api/settings/quota-reset-webhook";
const configured = { enabled: true, kinds: ["scheduled", "unexpected"], urlConfigured: true,
  signingSecretConfigured: true, pending: 0, lastDelivery: null };

describe("Quota reset webhook settings", () => {
  it("reveals the saved destination only on demand without editing it", async () => {
    const user = userEvent.setup();
    let reads = 0;
    server.use(http.get(path, () => HttpResponse.json(configured)),
      http.get(`${path}/destination`, () => {
        reads += 1;
        return HttpResponse.json({ url: "https://example.com/saved-secret" });
      }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    expect(reads).toBe(0);
    expect(screen.queryByLabelText("Saved webhook URL")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reveal saved URL" }));
    expect(await screen.findByLabelText("Saved webhook URL")).toHaveValue("https://example.com/saved-secret");
    expect(screen.getByLabelText("HTTPS webhook URL")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Hide saved URL" }));
    expect(screen.queryByLabelText("Saved webhook URL")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reveal saved URL" }));
    await screen.findByLabelText("Saved webhook URL");
    expect(reads).toBe(2);
  });

  it("reports reveal failures without displaying a destination", async () => {
    server.use(http.get(path, () => HttpResponse.json(configured)),
      http.get(`${path}/destination`, () => HttpResponse.json({ error: { code: "permission_denied", message: "Denied" } }, { status: 403 })));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await userEvent.click(await screen.findByRole("button", { name: "Reveal saved URL" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to reveal the saved URL");
    expect(screen.queryByLabelText("Saved webhook URL")).not.toBeInTheDocument();
  });
  it("reveals only the URL draft and restores masking after saving", async () => {
    const user = userEvent.setup();
    let saved: unknown;
    server.use(http.get(path, () => HttpResponse.json(configured)), http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json(configured);
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    const input = screen.getByLabelText("HTTPS webhook URL");
    expect(input).toHaveValue("");
    expect(input).toHaveAttribute("type", "password");
    await user.type(input, "https://example.com/private-token");
    await user.click(screen.getByRole("button", { name: "Show webhook URL" }));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("https://example.com/private-token");
    expect(saved).toBeUndefined();
    expect(screen.getByLabelText("Optional signing secret (16+ characters)")).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Hide webhook URL" }));
    expect(input).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Show webhook URL" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(input).toHaveValue(""));
    expect(input).toHaveAttribute("type", "password");
    expect(saved).toMatchObject({ url: "https://example.com/private-token" });
  });

  it("saves destination and filters without requiring an existing secret again", async () => {
    const user = userEvent.setup();
    let saved: unknown;
    server.use(http.get(path, () => HttpResponse.json(configured)), http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json(configured);
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    await user.click(screen.getByLabelText("Scheduled resets"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).toEqual({ enabled: true, kinds: ["unexpected"], clearUrl: false, clearSigningSecret: false }));
  });

  it("removing a destination disables delivery and sends no masked placeholder", async () => {
    const user = userEvent.setup(); let saved: unknown;
    server.use(http.get(path, () => HttpResponse.json(configured)), http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json({ ...configured, enabled: false, urlConfigured: false });
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    await user.click(screen.getByLabelText("Remove destination (disables delivery)"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).toMatchObject({ enabled: false, clearUrl: true }));
    expect(saved).not.toHaveProperty("url");
  });

  it("queues a test and displays delivery status", async () => {
    server.use(http.get(path, () => HttpResponse.json(configured)),
      http.post(`${path}/test`, () => HttpResponse.json({ eventId: "test-event" })));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    await userEvent.click(screen.getByRole("button", { name: "Test delivery" }));
    expect(await screen.findByText("Test queued; delivery status updates automatically.")).toBeInTheDocument();
  });

  it("disables all mutation controls for read-only users", async () => {
    server.use(http.get(path, () => HttpResponse.json(configured)));
    renderWithProviders(<QuotaResetWebhookSettings disabled />);
    await screen.findAllByPlaceholderText("Configured — leave blank to keep");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Test delivery" })).toBeDisabled();
    expect(screen.getByLabelText("HTTPS webhook URL")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reveal saved URL" })).toBeDisabled();
  });
});
