import { Pencil } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  browserTimeZone,
  findSubscriptionEnd,
  fromLocalDateTimeInput,
  toLocalDateTimeInput,
  useAccountSubscriptionEnds,
  useSetAccountSubscriptionEnd,
  type AccountSubscriptionTarget,
} from "@/features/accounts/account-subscriptions";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline, formatRelative } from "@/utils/formatters";

/** Operator-set end of a cancelled subscription. It only informs quota projections and never acts on the account. */
export function AccountSubscriptionEndPanel({
  target,
  readOnly,
}: {
  target: AccountSubscriptionTarget;
  readOnly: boolean;
}) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const { data: ends } = useAccountSubscriptionEnds();
  const setEnd = useSetAccountSubscriptionEnd(target);
  const endsAt = findSubscriptionEnd(ends, target);
  const [draft, setDraft] = useState<string | null>(null);
  const editing = draft !== null;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);

  const save = async (value: string | null) => {
    try {
      await setEnd.mutateAsync(value);
    } catch {
      return; // Stay in edit mode; the mutation reports the error.
    }
    setDraft(null);
  };

  const remainingMs = endsAt !== null ? Date.parse(endsAt) - now : null;
  const timeZone = browserTimeZone();

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[13px] font-medium">
          {t("accounts.detail.subscriptionEnd.title")}
        </h3>
        {!readOnly && !editing ? (
          <Button
            type="button"
            size="icon-xs"
            variant="ghost"
            className="text-muted-foreground"
            aria-label={t("accounts.detail.subscriptionEnd.edit")}
            title={t("accounts.detail.subscriptionEnd.edit")}
            onClick={() => setDraft(endsAt !== null ? toLocalDateTimeInput(endsAt) : "")}
          >
            <Pencil className="h-3 w-3" />
          </Button>
        ) : null}
      </div>
      {editing ? (
        <div className="space-y-2">
          <Input
            type="datetime-local"
            aria-label={t("accounts.detail.subscriptionEnd.label", { zone: timeZone })}
            className="h-8 text-xs"
            value={draft}
            autoFocus
            disabled={setEnd.isPending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                setDraft(null);
              }
            }}
          />
          <p className="text-[11px] text-muted-foreground">
            {t("accounts.detail.subscriptionEnd.zoneHint", { zone: timeZone })}
          </p>
          <div className="flex justify-end gap-2">
            {endsAt !== null ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="mr-auto h-7 text-xs"
                disabled={setEnd.isPending}
                onClick={() => void save(null)}
              >
                {t("accounts.detail.subscriptionEnd.clear")}
              </Button>
            ) : null}
            <Button type="button" size="sm" variant="outline" className="h-7 text-xs" onClick={() => setDraft(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="button"
              size="sm"
              className="h-7 text-xs"
              disabled={setEnd.isPending || draft === ""}
              onClick={() => void save(fromLocalDateTimeInput(draft))}
            >
              {t("common.actions.save")}
            </Button>
          </div>
        </div>
      ) : endsAt !== null && remainingMs !== null ? (
        <p className="text-xs tabular-nums">
          {t(remainingMs > 0 ? "accounts.detail.subscriptionEnd.endsAt" : "accounts.detail.subscriptionEnd.passedAt", {
            time: formatDateTimeInline(endsAt, dateDisplayFormat),
            zone: timeZone,
          })}
          {remainingMs > 0 ? <span className="ml-1.5 text-muted-foreground">{formatRelative(remainingMs)}</span> : null}
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">{t("accounts.detail.subscriptionEnd.empty")}</p>
      )}
    </div>
  );
}
