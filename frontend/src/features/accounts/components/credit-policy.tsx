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
  return <div className="flex min-w-0 flex-col gap-1">
    <div className="flex min-w-0 items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2 text-[13px] font-medium">
        <Coins className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        {t("accounts.actions.creditPolicy")}
      </div>
      <Select value={policy} onValueChange={(value) => onChange(value as AccountCreditPolicy)} disabled={disabled}>
        <SelectTrigger aria-label={t("accounts.actions.creditPolicy")} size="sm" className="h-8 w-36 min-w-0 text-xs"><SelectValue /></SelectTrigger>
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
