import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderProvidersList } from "@/features/accounts/test-utils";
import { renderWithProviders } from "@/test/utils";
import { OpenAIApiAccountDetail } from "./account-detail";
import { ModelPicker } from "./model-picker";
import { createOpenAIApiAccount } from "./test-fixtures";

vi.mock("@/features/accounts/components/provider-account-trends", () => ({
  ProviderAccountTrends: () => <div>Account trends</div>,
}));
vi.mock("@/features/accounts/components/account-color-picker", () => ({
  AccountColorPicker: () => null,
}));
vi.mock("@/features/accounts/components/account-note-panel", () => ({
  AccountNotePanel: () => null,
}));

const detailProps = () => ({
  readOnly: false,
  busy: false,
  onKey: vi.fn(),
  onCredit: vi.fn(),
  onRename: vi.fn(),
  onModels: vi.fn(),
  onImageModels: vi.fn(),
  onRefresh: vi.fn(),
  onToggle: vi.fn(),
  onDelete: vi.fn(),
  onRoutingPolicy: vi.fn(),
});

describe("OpenAI API accounts", () => {
  it("lists the estimated credit and selections in the Providers table", () => {
    renderProvidersList({ openAIApiAccounts: [createOpenAIApiAccount()] });
    const row = screen.getByTestId("provider-account-row");
    expect(within(row).getByText("$37.50")).toBeInTheDocument();
    expect(within(row).getByText("1 model · 1 image")).toBeInTheDocument();
    expect(row.querySelector("img")).toHaveAttribute("data-provider", "openai_apikey");
  });

  it("shows spend only when no monthly credit is configured", () => {
    const account = createOpenAIApiAccount({
      credit: {
        cycleStart: "2026-11-01T00:00:00Z",
        cycleEnd: "2026-12-01T00:00:00Z",
        spentUsd: 3,
        monthlyCreditUsd: null,
        remainingUsd: null,
        exhaustedUntil: null,
      },
    });
    renderProvidersList({ openAIApiAccounts: [account] });
    const row = screen.getByTestId("provider-account-row");
    expect(within(row).getByText("Not set")).toBeInTheDocument();
    expect(within(row).getByText("$3.00 spent this cycle")).toBeInTheDocument();
  });

  it("treats an OpenAI billing refusal as used-up credit", () => {
    const account = createOpenAIApiAccount();
    account.credit.exhaustedUntil = new Date(Date.now() + 86_400_000).toISOString();
    renderWithProviders(<OpenAIApiAccountDetail account={account} {...detailProps()} />);
    expect(screen.getByText("Used up")).toBeInTheDocument();
    expect(screen.getByText(/OpenAI reports the API credit as used up/)).toBeInTheDocument();
  });

  it("separates text and image models in the detail settings and picker", async () => {
    const account = createOpenAIApiAccount();
    const props = detailProps();
    renderWithProviders(<OpenAIApiAccountDetail account={account} {...props} />);
    expect(screen.getByText("Spent this cycle").nextSibling).toHaveTextContent("$12.50");

    const onSave = vi.fn().mockResolvedValue(undefined);
    const picker = render(
      <ModelPicker account={account} kind="text" busy={false} onClose={vi.fn()} onSave={onSave} />,
    );
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByText("GPT-6.2 Astra")).toBeInTheDocument();
    expect(dialog.queryByText("gpt-image-2.5-sunburst")).not.toBeInTheDocument();
    await userEvent.click(dialog.getByRole("checkbox", { name: "GPT-6 Luna" }));
    await userEvent.click(dialog.getByRole("button", { name: "Save 2 models" }));
    expect(onSave).toHaveBeenCalledWith([
      { model: "gpt-6.2-astra" },
      { model: "gpt-image-2.5-sunburst" },
      { model: "gpt-6-luna" },
    ]);
    picker.unmount();

    render(<ModelPicker account={account} kind="image" busy={false} onClose={vi.fn()} onSave={onSave} />);
    const images = within(screen.getByRole("dialog"));
    expect(images.getByText("gpt-image-2.5-sunburst")).toBeInTheDocument();
    expect(images.queryByText("GPT-6.2 Astra")).not.toBeInTheDocument();
  });
});
