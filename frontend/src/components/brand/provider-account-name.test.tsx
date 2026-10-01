import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProviderAccountName } from "./provider-account-name";

describe("ProviderAccountName", () => {
  it.each(["codex", "claude", "openrouter"] as const)("renders a local decorative %s mark", (provider) => {
    const { container } = render(<ProviderAccountName provider={provider}><span className="privacy-blur">Private account</span></ProviderAccountName>);
    const mark = container.querySelector("img")!;
    expect(mark).toHaveAttribute("src", `/images/providers/${provider === "codex" ? "openai" : provider}.svg`);
    expect(mark).toHaveAttribute("alt", "");
    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(mark).toHaveClass("size-4", "shrink-0", "dark:invert");
    expect(mark).not.toHaveClass("privacy-blur");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Private account")).toHaveClass("privacy-blur");
  });
  it("does not label an unknown provider", () => {
    const { container } = render(<ProviderAccountName provider={null}>Unassigned</ProviderAccountName>);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("Unassigned")).toBeVisible();
  });
});
