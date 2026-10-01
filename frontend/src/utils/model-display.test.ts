import { describe, expect, it } from "vitest";
import { modelDisplayName } from "./model-display";

describe("modelDisplayName", () => {
  it.each([
    ["gpt-6-astra", "GPT 6 Astra"],
    ["gpt-5.1-codex-mini", "GPT 5.1 Codex Mini"],
    ["anthropic/claude-haiku-4-5-20251001", "Claude Haiku 4.5"],
    ["openrouter/z-ai/glm-5.3-flash", "GLM 5.3 Flash"],
    ["openrouter/qwen/qwen3.8-27b:free", "Qwen3.8 27b (Free)"],
    ["custom-model", "Custom Model"],
    ["", "--"],
  ])("makes historical ID %s readable", (id, expected) => {
    expect(modelDisplayName(id)).toBe(expected);
  });
  it("uses custom catalog names without reformatting them", () => {
    expect(modelDisplayName("openrouter/vendor/id", "Vendor: My Custom Model")).toBe("Vendor: My Custom Model");
  });
  it("formats catalog entries that still use a technical slug as their name", () => {
    expect(modelDisplayName("anthropic/claude-opus-5-5", "claude-opus-5-5")).toBe("Claude Opus 5.5");
  });
});
