import { HttpResponse, http } from "msw";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import App from "@/App";
import { createApiKey, createApiKeyCreateResponse, createApiKeyUsage7Day } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

function getDialogFooterClose(dialog: HTMLElement): HTMLElement {
	return within(dialog)
		.getAllByRole("button", { name: "Close" })
		.find((button) => button.getAttribute("data-slot") === "button") as HTMLElement;
}

describe("api keys page integration", () => {
	beforeEach(() => {
		window.history.pushState({}, "", "/keys");
	});

	it("lists keys, filters them by search, and opens one from its row", async () => {
		const user = userEvent.setup();
		renderWithProviders(<App />);

		expect(await screen.findByRole("heading", { name: "API Keys" })).toBeInTheDocument();
		const list = await screen.findByTestId("api-keys-list");
		await waitFor(() => expect(within(list).getAllByTestId("api-key-row")).toHaveLength(2));

		await user.type(within(list).getByPlaceholderText("Search API keys..."), "Read only");
		const rows = within(list).getAllByTestId("api-key-row");
		expect(rows).toHaveLength(1);

		await user.click(within(rows[0]).getByText("Read only key"));
		expect(await screen.findByRole("heading", { name: "Read only key" })).toBeInTheDocument();
		expect(window.location.pathname).toBe("/keys/key_2");
		expect(screen.getByTestId("api-key-rail")).toBeInTheDocument();
	});

	it("opens a key directly from its URL", async () => {
		window.history.pushState({}, "", "/keys/key_2");
		renderWithProviders(<App />);

		expect(await screen.findByRole("heading", { name: "Read only key" })).toBeInTheDocument();
		expect(screen.getByTestId("api-key-detail")).toHaveAttribute("data-tab", "overview");
	});

	it("creates a key, shows the one-time key dialog, and refreshes the list", async () => {
		const user = userEvent.setup();
		renderWithProviders(<App />);

		await user.click(await screen.findByRole("button", { name: "Create API Key" }));
		const createDialog = await screen.findByRole("dialog", { name: "Create API key" });
		await user.type(within(createDialog).getByLabelText("Name"), "Created from APIs page");
		await user.click(within(createDialog).getByRole("button", { name: "Create" }));

		const dialog = await screen.findByRole("dialog", { name: "API key created" });
		expect(within(dialog).getByText(/sk-test-generated-/)).toBeInTheDocument();
		expect(within(dialog).getByText(/It will not be shown again/)).toBeInTheDocument();

		await user.click(getDialogFooterClose(dialog));
		expect(await within(screen.getByTestId("api-keys-list")).findByText("Created from APIs page")).toBeInTheDocument();
	});

	it("creates a key with a selectable reasoning-effort policy", async () => {
		const user = userEvent.setup();
		let requestBody: unknown;
		server.use(
			http.post("/api/api-keys/", async ({ request }) => {
				requestBody = await request.json();
				return HttpResponse.json(createApiKeyCreateResponse({ name: "Selectable effort key" }));
			}),
		);
		renderWithProviders(<App />);

		await user.click(await screen.findByRole("button", { name: "Create API Key" }));
		const createDialog = await screen.findByRole("dialog", { name: "Create API key" });
		await user.type(within(createDialog).getByLabelText("Name"), "Selectable effort key");
		await user.click(within(createDialog).getByRole("button", { name: "Allowed efforts: All efforts" }));
		await user.click(screen.getByRole("menuitemcheckbox", { name: /^Low$/ }));
		await user.keyboard("{Escape}");

		expect(within(createDialog).getByLabelText("Enforced Effort")).toBeDisabled();

		await user.click(within(createDialog).getByRole("button", { name: "Create" }));
		await waitFor(() => {
			expect(requestBody).toMatchObject({
				allowedReasoningEfforts: ["low"],
				enforcedReasoningEffort: null,
			});
		});
	});

	it("edits, toggles, regenerates, and deletes a key", async () => {
		window.history.pushState({}, "", "/keys/key_1/settings");
		const user = userEvent.setup();
		renderWithProviders(<App />);

		const nameInput = await screen.findByLabelText("Name");
		await user.clear(nameInput);
		await user.type(nameInput, "Updated from APIs page");
		await user.click(screen.getByRole("button", { name: "Save changes" }));

		expect(await screen.findByRole("heading", { name: "Updated from APIs page" })).toBeInTheDocument();
		await waitFor(() => expect(screen.queryByRole("region", { name: "Unsaved changes" })).not.toBeInTheDocument());

		await user.click(within(screen.getByRole("group", { name: "Key view" })).getByRole("button", { name: /overview/i }));
		expect(window.location.pathname).toBe("/keys/key_1");

		await user.click(screen.getByRole("button", { name: "Disable" }));
		expect(await screen.findByText("This key is disabled. Requests with it are refused.")).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Regenerate" }));
		const regeneratedDialog = await screen.findByRole("dialog", { name: "API key created" });
		expect(within(regeneratedDialog).getByText(/sk-test-regenerated-key_1/)).toBeInTheDocument();
		await user.click(getDialogFooterClose(regeneratedDialog));

		await user.click(screen.getByRole("button", { name: "More actions" }));
		await user.click(await screen.findByRole("menuitem", { name: "Delete key…" }));
		const confirmDialog = await screen.findByRole("alertdialog", { name: "Delete API key" });
		await user.click(within(confirmDialog).getByRole("button", { name: "Delete" }));

		await waitFor(() => expect(window.location.pathname).toBe("/keys"));
		await waitFor(() => expect(screen.queryByText("Updated from APIs page")).not.toBeInTheDocument());
	});

	it("shows backend errors from API mutations in the page alert", async () => {
		const user = userEvent.setup();
		server.use(
			http.post("/api/api-keys/", () => {
				return HttpResponse.json(
					{ error: { code: "invalid_api_key_payload", message: "Invalid create payload" } },
					{ status: 400 },
				);
			}),
		);

		renderWithProviders(<App />);

		await user.click(await screen.findByRole("button", { name: "Create API Key" }));
		const createDialog = await screen.findByRole("dialog", { name: "Create API key" });
		await user.type(within(createDialog).getByLabelText("Name"), "Broken create");
		await user.click(within(createDialog).getByRole("button", { name: "Create" }));

		expect(await screen.findByText("Invalid create payload")).toBeInTheDocument();
	});

	it("describes setup when there are no API keys", async () => {
		server.use(http.get("/api/api-keys/", () => HttpResponse.json([])));

		renderWithProviders(<App />);

		expect(await screen.findByRole("heading", { name: "API Keys" })).toBeInTheDocument();
		expect(await screen.findByText("No API keys yet")).toBeInTheDocument();
	});

	it("shows the last 7 days and access returned by the API on a key's overview", async () => {
		window.history.pushState({}, "", "/keys/key_custom");
		server.use(
			http.get("/api/api-keys/", () =>
				HttpResponse.json([
					createApiKey({
						id: "key_custom",
						name: "Custom analytics key",
						allowedModels: null,
						expiresAt: null,
						usageSummary: {
							requestCount: 42,
							totalTokens: 12_000,
							cachedInputTokens: 3_000,
							totalCostUsd: 0.42,
							pricedRequests: 42,
							unpricedRequests: 0,
							unmeteredRequests: 0,
							coverageUnknown: false,
						},
					}),
				]),
			),
			http.get("/api/api-keys/:keyId/usage-7d", ({ params }) =>
				HttpResponse.json(
					createApiKeyUsage7Day({
						keyId: String(params.keyId),
						totalTokens: 12_000,
						cachedInputTokens: 3_000,
						totalRequests: 42,
						totalCostUsd: 0.42,
					}),
				),
			),
		);

		renderWithProviders(<App />);

		expect(await screen.findByRole("heading", { name: "Custom analytics key" })).toBeInTheDocument();
		const lastWeek = screen.getByTestId("api-key-last-week");
		expect(await within(lastWeek).findByText("12K")).toBeInTheDocument();
		expect(within(lastWeek).getByText("3K cached")).toBeInTheDocument();
		expect(within(lastWeek).getByText("42")).toBeInTheDocument();
		expect(within(lastWeek).getByText(/\$0\.42/)).toBeInTheDocument();
		expect(within(screen.getByTestId("api-key-access")).getByText("All models")).toBeInTheDocument();
	});
});
