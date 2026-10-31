import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { get, put } from "@/lib/api-client";
import type { AccountColorTarget } from "@/features/accounts/account-colors";

export const ACCOUNT_SUBSCRIPTIONS_QUERY_KEY = ["account-subscriptions"] as const;

const AccountSubscriptionEndSchema = z.object({
  accountId: z.string().nullable(),
  modelSourceId: z.string().nullable(),
  endsAt: z.iso.datetime({ offset: true }),
});

const AccountSubscriptionEndsResponseSchema = z.object({
  ends: z.array(AccountSubscriptionEndSchema),
});

export type AccountSubscriptionEnd = z.infer<typeof AccountSubscriptionEndSchema>;

/** A Codex account, or a Claude or Antigravity model source. */
export type AccountSubscriptionTarget = AccountColorTarget;

export function findSubscriptionEnd(
  ends: AccountSubscriptionEnd[] | undefined,
  target: AccountSubscriptionTarget,
): string | null {
  const entry = ends?.find((end) =>
    "accountId" in target ? end.accountId === target.accountId : end.modelSourceId === target.modelSourceId,
  );
  return entry?.endsAt ?? null;
}

/** `YYYY-MM-DDTHH:mm` in local time, the value format of a datetime-local input. */
export function toLocalDateTimeInput(iso: string): string {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** The UTC instant of a datetime-local value, which is read as local time. */
export function fromLocalDateTimeInput(value: string): string {
  return new Date(value).toISOString();
}

/** The browser's IANA time zone, in which end dates are entered and shown. */
export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function useAccountSubscriptionEnds() {
  return useQuery({
    queryKey: ACCOUNT_SUBSCRIPTIONS_QUERY_KEY,
    queryFn: () => get("/api/account-subscriptions", AccountSubscriptionEndsResponseSchema),
    select: (data) => data.ends,
  });
}

export function useSetAccountSubscriptionEnd(target: AccountSubscriptionTarget) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const path =
    "accountId" in target
      ? `/api/account-subscriptions/accounts/${encodeURIComponent(target.accountId)}`
      : `/api/account-subscriptions/model-sources/${encodeURIComponent(target.modelSourceId)}`;
  return useMutation({
    mutationFn: (endsAt: string | null) => put(path, AccountSubscriptionEndsResponseSchema, { body: { endsAt } }),
    onSuccess: (data) => {
      client.setQueryData(ACCOUNT_SUBSCRIPTIONS_QUERY_KEY, data);
      // The weekly pace (overview and projections) and depletion (projections) read the end date.
      void client.invalidateQueries({ queryKey: ["dashboard", "overview"] });
      void client.invalidateQueries({ queryKey: ["dashboard", "projections"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("accounts.toasts.subscriptionEndUpdateFailed"));
    },
  });
}
