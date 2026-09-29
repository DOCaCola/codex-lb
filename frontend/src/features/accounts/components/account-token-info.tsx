import { useTranslation } from "react-i18next";
import { AccountInfoPanel } from "./account-info-panel";

import type { AccountSummary } from "@/features/accounts/schemas";
import {
  formatAccessTokenLabel,
  formatIdTokenLabel,
  formatRefreshTokenLabel,
} from "@/utils/formatters";

export type AccountTokenInfoProps = {
  account: AccountSummary;
};

export function AccountTokenInfo({ account }: AccountTokenInfoProps) {
  const { t } = useTranslation();
  return <AccountInfoPanel title={t("accounts.tokenInfo.title")} rows={[
    { label: t("accounts.tokenInfo.access"), value: formatAccessTokenLabel(account.auth) },
    { label: t("accounts.tokenInfo.refresh"), value: formatRefreshTokenLabel(account.auth) },
    { label: t("accounts.tokenInfo.idToken"), value: formatIdTokenLabel(account.auth) },
  ]} />;
}
