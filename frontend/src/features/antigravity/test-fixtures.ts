import type { AntigravityAccount, AntigravityWindow } from "./api";

export function createAntigravityWindow(
  overrides: Partial<AntigravityWindow> & Pick<AntigravityWindow, "family" | "window">,
): AntigravityWindow {
  return { usedPercent: 0, resetsAt: null, exhausted: false, ...overrides };
}

export function createAntigravityAccount(overrides: Partial<AntigravityAccount> = {}): AntigravityAccount {
  return {
    id: "antigravity-test",
    name: "Antigravity Test",
    email: "person@example.com",
    projectId: "project-1",
    isEnabled: true,
    routingPolicy: "normal",
    maxConcurrency: null,
    credentialStatus: "ready",
    hold: null,
    holdReason: null,
    holdAt: null,
    expiresAt: "2026-10-29T20:00:00Z",
    planType: "pro",
    quotaWeight: 1,
    state: {
      subscription: null,
      catalog: [],
      default_model: null,
      all_models: true,
      selections: [],
      metadata: {},
      verification: null,
    },
    windows: [
      createAntigravityWindow({ family: "gemini", window: "five_hour", usedPercent: 10 }),
      createAntigravityWindow({ family: "gemini", window: "weekly", usedPercent: 40 }),
      createAntigravityWindow({ family: "claude", window: "five_hour", usedPercent: 70 }),
      createAntigravityWindow({ family: "claude", window: "weekly", usedPercent: 20 }),
    ],
    quotaFresh: true,
    cooldowns: [],
    ...overrides,
  };
}
