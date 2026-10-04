import { act, fireEvent, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { createApiKeyUsage7Day } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { accountColorPalette } from "@/features/accounts/account-colors";

import { AccountCostDonut } from "./account-cost-donut";

function cssColor(hex: string): string {
	const probe = document.createElement("span");
	probe.style.backgroundColor = hex;
	return probe.style.backgroundColor;
}

vi.mock("@/components/lazy-recharts", () => ({
	Cell: () => null,
	PieChart: ({ children }: { children: ReactNode }) => <svg>{children}</svg>,
	Pie: ({
		children,
		data,
		onMouseEnter,
		onMouseLeave,
	}: {
		children: ReactNode;
		data: Array<{ id: string }>;
		onMouseEnter?: (entry: { payload: { id: string } }, index: number) => void;
		onMouseLeave?: () => void;
	}) => (
		<>
			{data.map((entry, index) => (
				<g
					key={entry.id}
					className="recharts-pie-sector"
					onMouseEnter={() => onMouseEnter?.({ payload: entry }, index)}
					onMouseLeave={() => onMouseLeave?.()}
				/>
			))}
			{children}
		</>
	),
	Sector: () => <path />,
}));

describe("AccountCostDonut", () => {
	it("highlights the matching legend row when a legend item is hovered", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 0.75,
			accountCosts: [
				{ accountId: "acc-1", name: "a@example.com", costUsd: 0.45, isDeleted: false },
				{ accountId: "acc-2", name: "b@example.com", costUsd: 0.3, isDeleted: false },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		const legendRow = screen.getByTestId("account-cost-legend-0");
		fireEvent.mouseEnter(legendRow);
		expect(legendRow).toHaveAttribute("data-active", "true");

		fireEvent.mouseLeave(legendRow);
		expect(legendRow).toHaveAttribute("data-active", "false");
	});

	it("highlights the matching legend row when a pie slice is hovered", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 0.75,
			accountCosts: [
				{ accountId: "acc-1", name: "a@example.com", costUsd: 0.45, isDeleted: false },
				{ accountId: "acc-2", name: "b@example.com", costUsd: 0.3, isDeleted: false },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		const slices = document.querySelectorAll(".recharts-pie-sector");
		fireEvent.mouseEnter(slices[0]!);

		expect(screen.getByTestId("account-cost-legend-0")).toHaveAttribute("data-active", "true");
	});

	it("limits the legend viewport to five visible rows before scrolling", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 2.8,
			accountCosts: Array.from({ length: 6 }, (_, index) => ({
				accountId: `acc-${index}`,
				name: `user${index}@example.com`,
				costUsd: 0.4 + index * 0.05,
				isDeleted: false,
			})),
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		// jsdom 30 simplifies calc() during serialization; authored: calc(5 * 1.75rem + 4 * 0rem)
		expect(screen.getByTestId("account-cost-legend-list").style.maxHeight).toBe("calc(8.75rem)");
		expect(screen.getByTestId("account-cost-legend-5")).toBeInTheDocument();
	});

	it("renders the legend below the donut and omits the header total summary", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 0.75,
			accountCosts: [
				{ accountId: "acc-1", name: "a@example.com", costUsd: 0.45, isDeleted: false },
				{ accountId: "acc-2", name: "b@example.com", costUsd: 0.3, isDeleted: false },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		expect(screen.queryByTestId("account-cost-total")).not.toBeInTheDocument();
		expect(screen.getByTestId("account-cost-legend-list")).toHaveClass("w-full");
	});

	it("blurs active account labels but not deleted account labels in privacy mode", () => {
		act(() => usePrivacyStore.setState({ blurred: true }));
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 0.75,
			accountCosts: [
				{ accountId: "acc-1", name: "a@example.com", costUsd: 0.45, isDeleted: false },
				{ accountId: null, name: null, costUsd: 0.3, isDeleted: true },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		expect(screen.getByText("a@example.com")).toHaveClass("privacy-blur");
		expect(screen.getByText("Deleted Account")).not.toHaveClass("privacy-blur");
		act(() => usePrivacyStore.setState({ blurred: false }));
	});

	it("marks provider accounts with their slice-coloured logo and others with a dot", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 1,
			accountCosts: [
				{ accountId: "acc-1", provider: "codex", name: "Andy Alpha", costUsd: 0.4, isDeleted: false },
				{ modelSourceId: "src-claude", provider: "claude", name: "DOCa Claude", costUsd: 0.3, isDeleted: false },
				{ accountId: null, name: null, costUsd: 0.2, isDeleted: false },
				{ accountId: null, provider: "openrouter", name: "Removed", costUsd: 0.1, isDeleted: true },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		const codexLogo = screen.getByTestId("account-cost-legend-0").querySelector("[data-provider]");
		expect(screen.getByText("Andy Alpha")).toBeInTheDocument();
		expect(codexLogo).toHaveAttribute("data-provider", "codex");
		expect((codexLogo as HTMLElement).style.backgroundColor).not.toBe("");
		const claudeRow = screen.getByTestId("account-cost-legend-1");
		expect(claudeRow).toHaveTextContent("DOCa Claude");
		expect(claudeRow.querySelector("[data-provider]")).toHaveAttribute("data-provider", "claude");
		for (const index of [2, 3]) {
			const row = screen.getByTestId(`account-cost-legend-${index}`);
			expect(row.querySelector("[data-provider]")).toBeNull();
			expect(row.querySelector(".rounded-full")).not.toBeNull();
		}
		expect(screen.getByText("Unknown Account")).toBeInTheDocument();
	});

	it("paints accounts in their chart colour and unknown entries in a colour no account here uses", () => {
		const usage = createApiKeyUsage7Day({
			totalCostUsd: 1,
			accountCosts: [
				{ accountId: "acc-1", provider: "codex", name: "Andy Alpha", costUsd: 0.5, isDeleted: false, chartColor: 7 },
				{ accountId: "acc-2", provider: "codex", name: "Andy Beta", costUsd: 0.3, isDeleted: false, chartColor: 0 },
				{ accountId: null, name: null, costUsd: 0.2, isDeleted: false },
			],
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		const palette = accountColorPalette(false);
		const logo = (index: number) =>
			screen.getByTestId(`account-cost-legend-${index}`).querySelector("[data-provider]") as HTMLElement;
		expect(logo(0).style.backgroundColor).toBe(cssColor(palette[7]));
		expect(logo(1).style.backgroundColor).toBe(cssColor(palette[0]));
		const unknownDot = screen.getByTestId("account-cost-legend-2").querySelector(".rounded-full") as HTMLElement;
		expect(unknownDot.style.backgroundColor).toBe(cssColor(palette[1]));
	});

	it("scrolls the hovered pie item into view in the legend list", async () => {
		const scrollIntoView = vi.fn();
		Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
			configurable: true,
			value: scrollIntoView,
		});

		const usage = createApiKeyUsage7Day({
			totalCostUsd: 5.6,
			accountCosts: Array.from({ length: 6 }, (_, index) => ({
				accountId: `acc-${index}`,
				name: `user${index}@example.com`,
				costUsd: 1 - index * 0.1,
				isDeleted: false,
			})),
		});

		renderWithProviders(
			<AccountCostDonut accountCosts={usage.accountCosts} totalCostUsd={usage.totalCostUsd} />,
		);

		const slices = document.querySelectorAll(".recharts-pie-sector");
		fireEvent.mouseEnter(slices[5]!);

		expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
	});
});
