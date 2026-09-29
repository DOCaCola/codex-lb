import { Flame, Shield, Route } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AccountRoutingPolicy } from "@/features/accounts/schemas";

export function RoutingPolicyBadge({
  policy,
}: {
  policy: AccountRoutingPolicy | undefined;
}) {
  const { t } = useTranslation();
  if (policy === "burn_first") {
    return (
      <Badge
        variant="outline"
        className="shrink-0 gap-1 border-amber-300 bg-amber-50 px-1.5 text-[11px] text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
      >
        <Flame className="h-3 w-3" aria-hidden="true" />
        {t("common.routingPolicies.burnFirst")}
      </Badge>
    );
  }
  if (policy === "preserve") {
    return (
      <Badge
        variant="outline"
        className="shrink-0 gap-1 border-sky-300 bg-sky-50 px-1.5 text-[11px] text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-300"
      >
        <Shield className="h-3 w-3" aria-hidden="true" />
        {t("common.routingPolicies.preserve")}
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className="shrink-0 px-1.5 text-[11px] text-muted-foreground"
    >
      {t("common.routingPolicies.normal")}
    </Badge>
  );
}


export function AccountRoutingPolicyControl({ policy, disabled, onChange }: {
  policy: AccountRoutingPolicy;
  disabled: boolean;
  onChange: (policy: AccountRoutingPolicy) => void;
}) {
  const { t } = useTranslation();
  return <div className="flex flex-col gap-2 rounded-md border bg-muted/30 p-3 sm:flex-row sm:items-center sm:gap-3">
    <div className="flex min-w-0 items-center gap-2 text-sm font-medium sm:min-w-36">
      <Route className="h-4 w-4 text-muted-foreground" />
      {t("accounts.actions.routingPolicy")}
    </div>
    <Select value={policy} onValueChange={(value) => onChange(value as AccountRoutingPolicy)} disabled={disabled}>
      <SelectTrigger aria-label={t("accounts.actions.routingPolicy")} size="sm" className="h-8 w-full min-w-0 text-xs sm:min-w-32 sm:flex-1"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="burn_first">{t("common.routingPolicies.burnFirst")}</SelectItem>
        <SelectItem value="normal">{t("common.routingPolicies.normal")}</SelectItem>
        <SelectItem value="preserve">{t("common.routingPolicies.preserve")}</SelectItem>
      </SelectContent>
    </Select>
  </div>;
}
