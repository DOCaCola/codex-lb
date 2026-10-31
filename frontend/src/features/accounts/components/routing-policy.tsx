import { Route } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AccountRoutingPolicy } from "@/features/accounts/schemas";

export function AccountRoutingPolicyControl({ policy, disabled, onChange }: {
  policy: AccountRoutingPolicy;
  disabled: boolean;
  onChange: (policy: AccountRoutingPolicy) => void;
}) {
  const { t } = useTranslation();
  return <div className="flex min-w-0 items-center justify-between gap-3">
    <div className="flex min-w-0 items-center gap-2 text-[13px] font-medium">
      <Route className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      {t("accounts.actions.routingPolicy")}
    </div>
    <Select value={policy} onValueChange={(value) => onChange(value as AccountRoutingPolicy)} disabled={disabled}>
      <SelectTrigger aria-label={t("accounts.actions.routingPolicy")} size="sm" className="h-8 w-36 min-w-0 text-xs"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="burn_first">{t("common.routingPolicies.burnFirst")}</SelectItem>
        <SelectItem value="normal">{t("common.routingPolicies.normal")}</SelectItem>
        <SelectItem value="preserve">{t("common.routingPolicies.preserve")}</SelectItem>
      </SelectContent>
    </Select>
  </div>;
}
