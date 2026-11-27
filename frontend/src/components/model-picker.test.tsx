import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ModelPicker, type ModelPickerGroup } from "@/components/model-picker";
import { renderWithProviders } from "@/test/utils";

const groups: ModelPickerGroup[] = [
  {
    id: "client",
    label: "Client requests",
    highlighted: true,
    options: [{ value: "gpt-image-2", label: "gpt-image-2", badge: "image" }],
  },
  {
    id: "openai",
    label: "OpenAI",
    options: [
      { value: "gpt-6-sol", label: "GPT-6 Sol" },
      { value: "gpt-6-old", label: "GPT-6 Old", disabled: true },
      { value: "gpt-6-luna", label: "GPT-6 Luna", note: "hidden" },
    ],
  },
];

function renderPicker(props: Partial<Parameters<typeof ModelPicker>[0]> = {}) {
  const onChange = vi.fn();
  renderWithProviders(
    <ModelPicker
      label="Model"
      value=""
      onChange={onChange}
      groups={groups}
      placeholder="Choose a model"
      searchPlaceholder="Search models"
      emptyText="Nothing to choose"
      {...props}
    />,
  );
  return onChange;
}

describe("ModelPicker", () => {
  it("keeps sections apart, filters by search and skips disabled options with the keyboard", async () => {
    const user = userEvent.setup();
    const onChange = renderPicker();
    await user.click(screen.getByRole("combobox", { name: "Model" }));

    expect(within(screen.getByRole("group", { name: "Client requests" })).getByRole("option", { name: "gpt-image-2, image" })).toBeVisible();
    expect(within(screen.getByRole("group", { name: "OpenAI" })).getAllByRole("option")).toHaveLength(3);

    const search = screen.getByRole("searchbox", { name: "Search models" });
    await user.type(search, "gpt-6");
    expect(screen.queryByRole("group", { name: "Client requests" })).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("gpt-6-luna");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("offers the typed name only when custom names are allowed and it is not listed", async () => {
    const user = userEvent.setup();
    const onChange = renderPicker({ allowCustom: true });
    await user.click(screen.getByRole("combobox", { name: "Model" }));
    const search = screen.getByRole("searchbox", { name: "Search models" });

    await user.type(search, "gpt-6-sol");
    expect(screen.queryByRole("option", { name: /^Use/ })).not.toBeInTheDocument();
    await user.clear(search);
    await user.type(search, "retired/model{Enter}");
    expect(onChange).toHaveBeenCalledWith("retired/model");
  });

  it("reports the toggle and distinguishes no matches from an empty list", async () => {
    const user = userEvent.setup();
    const onCheckedChange = vi.fn();
    renderPicker({ toggle: { label: "Show disabled models", checked: false, count: 4, onCheckedChange } });
    await user.click(screen.getByRole("combobox", { name: "Model" }));

    await user.click(screen.getByRole("switch", { name: "Show disabled models" }));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
    await user.type(screen.getByRole("searchbox", { name: "Search models" }), "claude");
    expect(screen.getByText("No matching models")).toBeVisible();
  });

  it("shows the empty text when no section offers a model", async () => {
    const user = userEvent.setup();
    renderPicker({ groups: [] });
    await user.click(screen.getByRole("combobox", { name: "Model" }));
    expect(screen.getByText("Nothing to choose")).toBeVisible();
  });
});
