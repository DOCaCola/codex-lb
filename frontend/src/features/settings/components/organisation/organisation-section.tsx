import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";

import { SpinnerBlock } from "@/components/ui/spinner";
import { useDashboardUsers } from "@/features/access/hooks";
import { useAuthStore, usePermission } from "@/features/auth/hooks/use-auth";
import {
  useAssignableRoles,
  useAuthProviders,
  useOrganisationMutations,
  useRoleMappings,
  useScimTokens,
} from "@/features/organisation/hooks";
import {
  companyLoginLabel,
  hasCompanyLogin,
  hasScimTokens,
  isLocalLoginRestricted,
  isOrganisationConfigured,
  oidcProvider,
  rulesOf,
  trustedHeaderProvider,
} from "@/features/organisation/rules";
import { AutomaticAccountsCard } from "@/features/settings/components/organisation/automatic-accounts-card";
import { GroupRulesCard } from "@/features/settings/components/organisation/group-rules-card";
import { LoginPolicyCard } from "@/features/settings/components/organisation/login-policy-card";
import { OidcCard } from "@/features/settings/components/organisation/oidc-card";
import { ReverseProxyCard } from "@/features/settings/components/organisation/reverse-proxy-card";
import { SettingsSection } from "@/features/settings/components/settings-layout";
import { useSettingsSection } from "@/features/settings/use-settings-section";
import {
  DEFAULT_SETTINGS_SECTION,
  ORGANISATION_REFUSED_HASH,
  settingsPath,
} from "@/features/settings/settings-links";
import { useHashTargetScroll } from "@/features/settings/use-hash-target-scroll";
import type { DashboardSettings } from "@/features/settings/schemas";

type DescriptionKey =
  | "organisation.group.oneLiner"
  | "organisation.group.summary"
  | "organisation.group.summaryRestricted"
  | "organisation.group.summaryPolicyOnly"
  | "organisation.group.summaryAutomatic"
  | "organisation.group.summaryAutomaticRestricted"
  | "organisation.group.summaryNamed"
  | "organisation.group.summaryNamedRestricted";

/**
 * The section's one-line description. It stays plain until something has been
 * set up; after that it counts what exists, from facts the session already
 * carries.
 *
 * A tightened login policy is configured state of its own: an install can have
 * it with no company login at all, and then the count sentence would be a lie.
 * A credential for automatic account management outlives the company sign-in
 * it was issued against, so that surviving fact gets its own sentence. With
 * exactly one company sign-in active the line names it, from the login hint
 * every session carries (`access_summary` lists provider kinds, never labels).
 */
function descriptionKeyFor({
  configured,
  companyLogin,
  automatic,
  restricted,
  named,
}: {
  configured: boolean;
  companyLogin: boolean;
  automatic: boolean;
  restricted: boolean;
  named: boolean;
}): DescriptionKey {
  if (!configured) {
    return "organisation.group.oneLiner";
  }
  if (!companyLogin) {
    if (automatic) {
      return restricted ? "organisation.group.summaryAutomaticRestricted" : "organisation.group.summaryAutomatic";
    }
    return "organisation.group.summaryPolicyOnly";
  }
  if (named) {
    return restricted ? "organisation.group.summaryNamedRestricted" : "organisation.group.summaryNamed";
  }
  return restricted ? "organisation.group.summaryRestricted" : "organisation.group.summary";
}

/** The section's cards and the queries they need. */
function OrganisationCards({
  settings,
  refusedOpen,
  disabled,
}: {
  settings: DashboardSettings;
  refusedOpen: boolean;
  disabled: boolean;
}) {
  const { t } = useTranslation();
  // The people list is `users:manage`, a different permission from the one that
  // gates this section. Without it the policy card cannot name the emergency
  // account; the roles come from the rules API instead, which this section holds.
  const canManageUsers = usePermission("users:manage");
  const canReadAudit = usePermission("audit:read");
  const providersQuery = useAuthProviders();
  const mappingsQuery = useRoleMappings();
  // The roles the caller may hand out, from the rules API and not the
  // `users:manage` list: this section belongs to `security:write`, and the
  // server has already applied the delegation rule its writes apply.
  const rolesQuery = useAssignableRoles();
  const usersQuery = useDashboardUsers(canManageUsers);
  const tokensQuery = useScimTokens();
  const mutations = useOrganisationMutations();
  const loading = providersQuery.isLoading || mappingsQuery.isLoading || rolesQuery.isLoading;
  // The card anchors (`#oidc`, `#organisation-login-policy`, …) sit behind the
  // spinner, so a cold deep link scrolls once the cards exist.
  useHashTargetScroll(!loading);

  if (loading) {
    return <SpinnerBlock />;
  }

  const provider = trustedHeaderProvider(providersQuery.data);
  const oidc = oidcProvider(providersQuery.data);
  const roles = rolesQuery.data ?? [];

  // Order per PLAN §4.8: company sign-in, reverse proxy, rules, login policy,
  // automatic account management. The login-policy card describes the local
  // sign-in every install has and the last card is offered to every install,
  // while the proxy cards describe a deployment that may simply not exist.
  // Saying so is a neutral fact about the topology, never a missing piece.
  // The policy card takes the people query whole: it is the only place that can
  // say "this could not be loaded", and `undefined` cannot tell pending from failed.
  return (
    <>
      {oidc === null ? null : <OidcCard provider={oidc} mutations={mutations} disabled={disabled} />}
      {provider === null ? (
        <p className="text-xs text-muted-foreground">{t("organisation.group.noReverseProxy")}</p>
      ) : (
        <>
          <ReverseProxyCard provider={provider} roles={roles} mutations={mutations} disabled={disabled} />
          <GroupRulesCard
            provider={provider}
            roles={roles}
            rules={rulesOf(mappingsQuery.data, provider)}
            mutations={mutations}
            canReadAudit={canReadAudit}
            refusedOpen={refusedOpen}
            disabled={disabled}
          />
        </>
      )}
      <LoginPolicyCard
        settings={settings}
        usersQuery={usersQuery}
        canSeeAccounts={canManageUsers}
        mutations={mutations}
        disabled={disabled}
      />
      <AutomaticAccountsCard
        tokensQuery={tokensQuery}
        providers={providersQuery.data}
        mutations={mutations}
        disabled={disabled}
      />
    </>
  );
}

/**
 * Settings → Organisation: what a company install needs and a single-person
 * install never meets. Only `security:write` holders see it; anyone else who
 * follows a link here lands on the default section.
 */
export function OrganisationSettingsSection() {
  const { t } = useTranslation();
  const { hash } = useLocation();
  const { settings, controlsDisabled } = useSettingsSection();
  const canWriteSecurity = usePermission("security:write");
  const accessSummary = useAuthStore((state) => state.accessSummary);
  const providers = useAuthStore((state) => state.loginHint.providers);

  if (!canWriteSecurity) {
    return <Navigate to={settingsPath(DEFAULT_SETTINGS_SECTION)} replace />;
  }

  // The operator's own word for their identity provider, quoted verbatim: the
  // banned-word rule governs the copy this product writes, not a customer's
  // name for their own system.
  const providerLabel = companyLoginLabel(providers);
  const descriptionKey = descriptionKeyFor({
    configured: isOrganisationConfigured(accessSummary),
    companyLogin: hasCompanyLogin(accessSummary),
    automatic: hasScimTokens(accessSummary),
    restricted: isLocalLoginRestricted(accessSummary),
    named: providerLabel !== null,
  });

  return (
    <SettingsSection
      section="organisation"
      description={
        <span data-testid="organisation-group-line">
          {t(descriptionKey, { count: accessSummary?.roleMappings ?? 0, provider: providerLabel ?? "" })}
        </span>
      }
    >
      <OrganisationCards
        settings={settings}
        refusedOpen={hash === ORGANISATION_REFUSED_HASH}
        disabled={controlsDisabled}
      />
    </SettingsSection>
  );
}
