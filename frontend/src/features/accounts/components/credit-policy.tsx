import { Coins } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AccountCreditPolicy } from "@/features/accounts/schemas";

export function AccountCreditPolicyControl({ policy, disabled, onChange }: {
  policy: AccountCreditPolicy;
  disabled: boolean;
  onChange: (policy: AccountCreditPolicy) => void;
}) {
  const { t } = useTranslation();
  return <div className="flex flex-col gap-2 rounded-md border bg-muted/30 p-3">
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      <div className="flex min-w-0 items-center gap-2 text-sm font-medium sm:min-w-36">
        <Coins className="h-4 w-4 text-muted-foreground" />
        {t("accounts.actions.creditPolicy")}
      </div>
      <Select value={policy} onValueChange={(value) => onChange(value as AccountCreditPolicy)} disabled={disabled}>
        <SelectTrigger aria-label={t("accounts.actions.creditPolicy")} size="sm" className="h-8 w-full min-w-0 text-xs sm:min-w-32 sm:flex-1"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="spend">{t("accounts.creditPolicies.spend")}</SelectItem>
          <SelectItem value="never">{t("accounts.creditPolicies.never")}</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <p className="text-[11px] text-muted-foreground">
      {policy === "never" ? t("accounts.creditPolicies.neverHint") : t("accounts.creditPolicies.spendHint")}
    </p>
  </div>;
}
