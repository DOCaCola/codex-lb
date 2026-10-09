import { describe, expect, it } from "vitest";

import {
  ACCESS_MY_SIGN_IN_PATH,
  ACCESS_PEOPLE_PATH,
  accessTabFromHash,
  ORGANISATION_SETTINGS_RETURN_URL,
  settingsPath,
} from "@/features/settings/settings-links";

describe("settings links", () => {
  it("addresses a section and optionally a card", () => {
    expect(settingsPath("routing")).toBe("/settings/routing");
    expect(settingsPath("organisation", "oidc")).toBe("/settings/organisation#oidc");
  });

  it("returns the sign-in flow to the company sign-in card", () => {
    // The backend's OIDC_SETTINGS_PATH names the same URL.
    expect(ORGANISATION_SETTINGS_RETURN_URL).toBe("/settings/organisation#oidc");
  });

  it("maps the Access card hashes to tabs", () => {
    expect(ACCESS_PEOPLE_PATH).toBe("/settings/access#people");
    expect(ACCESS_MY_SIGN_IN_PATH).toBe("/settings/access#my-sign-in");
    expect(accessTabFromHash("#people")).toBe("people");
    expect(accessTabFromHash("#my-sign-in")).toBe("my-sign-in");
    expect(accessTabFromHash("#totp")).toBe("my-sign-in");
    expect(accessTabFromHash("#firewall")).toBeNull();
    expect(accessTabFromHash("")).toBeNull();
  });
});
