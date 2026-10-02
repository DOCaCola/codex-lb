import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceTierMark } from "./service-tier-mark";

describe("ServiceTierMark", () => {
  it.each([
    ["priority", "Fast"],
    ["ultrafast", "Ultrafast"],
  ])("draws the %s glyph in the muted text color", (tier, label) => {
    render(<ServiceTierMark tier={tier} label={label} />);
    const mark = screen.getByRole("img", { name: label });
    expect(mark).toHaveAttribute("title", label);
    expect(mark).toHaveAttribute("data-service-tier", tier);
    expect(mark).toHaveClass("bg-current", "text-muted-foreground");
  });

  it("names tiers without a glyph", () => {
    render(<ServiceTierMark tier="flex" label="Flex" />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText("Flex")).toHaveClass("text-muted-foreground");
  });
});
