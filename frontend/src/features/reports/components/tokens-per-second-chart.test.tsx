import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { TokensPerSecondChart } from "./tokens-per-second-chart";

describe("TokensPerSecondChart", () => {
  it("explains estimated gateway sample eligibility without changing the chart layout", () => {
    renderWithProviders(<TokensPerSecondChart startDate="2026-10-01" endDate="2026-10-01" data={[]} />);
    expect(screen.getByText("Tokens per Second")).toHaveAttribute("title",
      "Claude and OpenRouter TPS are gateway estimates using reported output, including reasoning. Failed turns and observation windows under one second are excluded.");
  });
});
