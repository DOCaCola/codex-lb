import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { QuotaResetWebhookSettings } from "./quota-reset-webhook-settings";
import { renderWithProviders } from "@/test/utils";
import { server } from "@/test/mocks/server";

const path = "/api/settings/quota-reset-webhook";
const savedUrl = "https://example.com/saved-token";
const configured = { enabled: true, kinds: ["scheduled", "unexpected"], urlConfigured: true,
  signingSecretConfigured: true, pending: 0, lastDelivery: null };

async function loadedInput() {
  const input = screen.getByLabelText("HTTPS webhook URL");
  await waitFor(() => expect(input).toHaveValue(savedUrl));
  return input;
}

describe("Quota reset webhook settings", () => {
  beforeEach(() => {
    server.use(http.get(path, () => HttpResponse.json(configured)),
      http.get(`${path}/destination`, () => HttpResponse.json({ url: savedUrl })));
  });

  it("loads the saved URL masked and toggles visibility without editing", async () => {
    renderWithProviders(<QuotaResetWebhookSettings />);
    const input = await loadedInput();
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show webhook URL" }));
    expect(input).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Hide webhook URL" }));
    expect(input).toHaveAttribute("type", "password");
    expect(screen.queryByText("Remove destination (disables delivery)")).not.toBeInTheDocument();
  });

  it("clears the saved URL and disables delivery on save", async () => {
    let saved: unknown;
    server.use(http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json({ ...configured, enabled: false, urlConfigured: false });
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await userEvent.clear(await loadedInput());
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).toMatchObject({ enabled: false, clearUrl: true }));
    expect(saved).not.toHaveProperty("url");
  });

  it("saves URL replacements and restores masking", async () => {
    let saved: unknown;
    server.use(http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json(configured);
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    const input = await loadedInput();
    await userEvent.clear(input);
    await userEvent.type(input, "https://example.com/new");
    await userEvent.click(screen.getByRole("button", { name: "Show webhook URL" }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).toMatchObject({ url: "https://example.com/new", clearUrl: false }));
    await waitFor(() => expect(input).toHaveAttribute("type", "password"));
    expect(input).toHaveValue("https://example.com/new");
  });

  it("removes an existing signing secret through a saveable button", async () => {
    let saved: unknown;
    server.use(http.put(path, async ({ request }) => {
      saved = await request.json(); return HttpResponse.json({ ...configured, signingSecretConfigured: false });
    }));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await loadedInput();
    await userEvent.click(screen.getByRole("button", { name: "Remove signing secret" }));
    expect(screen.getByRole("button", { name: "Undo signing secret removal" })).toBeInTheDocument();
    expect(saved).toBeUndefined();
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).toMatchObject({ clearSigningSecret: true }));
    expect(saved).not.toHaveProperty("url");
    expect(saved).not.toHaveProperty("signingSecret");
  });

  it("does not offer removal when no signing secret exists", async () => {
    server.use(http.get(path, () => HttpResponse.json({ ...configured, signingSecretConfigured: false })));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await loadedInput();
    expect(screen.queryByRole("button", { name: "Remove signing secret" })).not.toBeInTheDocument();
  });

  it("blocks saves when destination loading fails", async () => {
    server.use(http.get(`${path}/destination`, () => HttpResponse.json({ error: { code: "permission_required", message: "Denied" } }, { status: 403 })));
    renderWithProviders(<QuotaResetWebhookSettings />);
    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have permission");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Retry loading URL" })).toBeInTheDocument();
  });

  it("explains authentication failures instead of blaming the URL", async () => {
    server.use(http.put(path, () => HttpResponse.json({ error: { code: "step_up_unavailable", message: "Unavailable" } }, { status: 403 })));
    renderWithProviders(<QuotaResetWebhookSettings />);
    await loadedInput();
    await userEvent.click(screen.getByLabelText("Scheduled resets"));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Identity verification is unavailable");
  });

  it("does not load URLs for read-only users", async () => {
    let reads = 0;
    server.use(http.get(`${path}/destination`, () => { reads += 1; return HttpResponse.json({ url: savedUrl }); }));
    renderWithProviders(<QuotaResetWebhookSettings disabled />);
    await screen.findByPlaceholderText("Configured — leave blank to keep");
    expect(reads).toBe(0);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(screen.getByLabelText("HTTPS webhook URL")).toBeDisabled();
  });
});
