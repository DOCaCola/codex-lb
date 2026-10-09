import type { Permission } from "@/features/auth/schemas";

// Settings is one route per section. A link names the section and, when it
// points at a card, that card's anchor as the hash.
export const SETTINGS_SECTIONS = [
  { id: "general", group: "workspace" },
  { id: "accounts", group: "workspace" },
  { id: "access", group: "workspace" },
  { id: "organisation", group: "workspace", requires: "security:write" },
  { id: "routing", group: "traffic" },
  { id: "models", group: "traffic" },
  { id: "upstream", group: "traffic" },
  { id: "automations", group: "operations" },
  { id: "data", group: "operations" },
  { id: "notifications", group: "operations" },
] as const satisfies readonly { id: string; group: string; requires?: Permission }[];

export type SettingsSectionId = (typeof SETTINGS_SECTIONS)[number]["id"];

export const DEFAULT_SETTINGS_SECTION: SettingsSectionId = "general";

export function settingsPath(section: SettingsSectionId, anchor?: string): string {
  return anchor === undefined ? `/settings/${section}` : `/settings/${section}#${anchor}`;
}

// Access card: `#people` selects the People tab, `#my-sign-in` the person's own
// controls, and `#totp` (the TOTP card's own id, inside those controls) selects
// the same tab and scrolls to the card.
export const ACCESS_PEOPLE_ANCHOR = "people";
export const ACCESS_MY_SIGN_IN_ANCHOR = "my-sign-in";
export const ACCESS_TOTP_ANCHOR = "totp";
export const ACCESS_PEOPLE_PATH = settingsPath("access", ACCESS_PEOPLE_ANCHOR);
export const ACCESS_MY_SIGN_IN_PATH = settingsPath("access", ACCESS_MY_SIGN_IN_ANCHOR);

export type AccessTab = "people" | "my-sign-in";

export function accessTabFromHash(hash: string): AccessTab | null {
  if (hash === `#${ACCESS_PEOPLE_ANCHOR}`) {
    return "people";
  }
  return hash === `#${ACCESS_MY_SIGN_IN_ANCHOR}` || hash === `#${ACCESS_TOTP_ANCHOR}` ? "my-sign-in" : null;
}

// Organisation cards. `#organisation-refused` opens the rules card's refused
// sign-ins sheet rather than naming a card.
export const ORGANISATION_LOGIN_POLICY_ID = "organisation-login-policy";
export const ORGANISATION_SCIM_ID = "organisation-automatic-accounts";
export const ORGANISATION_REFUSED_HASH = "#organisation-refused";
/**
 * The company sign-in card. The OIDC callback returns a completed pre-flight or
 * re-authentication to `OIDC_SETTINGS_PATH` (`app/modules/dashboard_auth/oidc_api.py`),
 * which is this URL; the two must not drift.
 */
export const ORGANISATION_OIDC_ID = "oidc";
export const ORGANISATION_SETTINGS_PATH = settingsPath("organisation");
export const ORGANISATION_SETTINGS_RETURN_URL = settingsPath("organisation", ORGANISATION_OIDC_ID);
