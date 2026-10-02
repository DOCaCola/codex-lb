import { describe, expect, it } from "vitest";

import i18n from "@/i18n";
import {
  isServiceTierDowngrade,
  serviceTierLabel,
  visibleServiceTier,
} from "@/utils/service-tiers";

describe("service tiers", () => {
  it("hides the implicit standard tier", () => {
    expect(visibleServiceTier("default")).toBeNull();
    expect(visibleServiceTier("auto")).toBeNull();
    expect(visibleServiceTier(null)).toBeNull();
    expect(visibleServiceTier(" Priority ")).toBe("priority");
  });

  it("detects only cheaper billed tiers as downgrades", () => {
    expect(isServiceTierDowngrade("priority", "flex")).toBe(true);
    expect(isServiceTierDowngrade("priority", "default")).toBe(true);
    expect(isServiceTierDowngrade("priority", "priority")).toBe(false);
    expect(isServiceTierDowngrade(null, "default")).toBe(false);
    expect(isServiceTierDowngrade("priority", null)).toBe(false);
  });

  it("uses readable tier names", () => {
    expect(serviceTierLabel("priority", i18n.t)).toBe("Fast");
    expect(serviceTierLabel("custom", i18n.t)).toBe("custom");
    expect(serviceTierLabel(null, i18n.t)).toBe("");
  });
});
