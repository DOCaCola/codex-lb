import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { useThemeStore } from "@/hooks/use-theme";
import { get, put } from "@/lib/api-client";
import { buildDonutPalette } from "@/utils/colors";

/** Selectable chart colours, in palette order: the six base colours, then their first shades. */
export const ACCOUNT_COLOR_KEYS = [
  "blue",
  "violet",
  "emerald",
  "amber",
  "pink",
  "cyan",
  "lightBlue",
  "darkViolet",
  "lightEmerald",
  "darkAmber",
  "lightPink",
  "darkCyan",
] as const;

export const ACCOUNT_COLORS_QUERY_KEY = ["account-colors"] as const;

const AccountColorSchema = z.object({
  accountId: z.string().nullable(),
  modelSourceId: z.string().nullable(),
  chartColor: z.number().int().nullable(),
  color: z.number().int(),
  automaticColor: z.number().int(),
});

const AccountColorsResponseSchema = z.object({
  colors: z.array(AccountColorSchema),
});

export type AccountColor = z.infer<typeof AccountColorSchema>;

/** A Codex account, or a model source (Claude, OpenRouter and other provider accounts). */
export type AccountColorTarget = { accountId: string } | { modelSourceId: string };

/** Theme colours of Codex accounts and of model sources, keyed by their IDs. */
export type AccountColorHexes = {
  accounts: ReadonlyMap<string, string>;
  modelSources: ReadonlyMap<string, string>;
};

export const NO_ACCOUNT_COLORS: AccountColorHexes = { accounts: new Map(), modelSources: new Map() };

export function accountColorPalette(isDark: boolean): string[] {
  return buildDonutPalette(ACCOUNT_COLOR_KEYS.length, isDark);
}

function matchesTarget(entry: AccountColor, target: AccountColorTarget): boolean {
  return "accountId" in target ? entry.accountId === target.accountId : entry.modelSourceId === target.modelSourceId;
}

export function findAccountColor(colors: AccountColor[] | undefined, target: AccountColorTarget) {
  return colors?.find((entry) => matchesTarget(entry, target));
}

export function useAccountColors() {
  return useQuery({
    queryKey: ACCOUNT_COLORS_QUERY_KEY,
    queryFn: () => get("/api/account-colors", AccountColorsResponseSchema),
    select: (data) => data.colors,
  });
}

/** Colour of every account for the theme in use; empty until the colours have loaded. */
export function useAccountColorHexes(): AccountColorHexes {
  const isDark = useThemeStore((s) => s.theme === "dark");
  const { data } = useAccountColors();
  return useMemo(() => {
    if (!data) {
      return NO_ACCOUNT_COLORS;
    }
    const palette = accountColorPalette(isDark);
    const accounts = new Map<string, string>();
    const modelSources = new Map<string, string>();
    for (const entry of data) {
      if (entry.accountId) {
        accounts.set(entry.accountId, palette[entry.color]);
      }
      if (entry.modelSourceId) {
        modelSources.set(entry.modelSourceId, palette[entry.color]);
      }
    }
    return { accounts, modelSources };
  }, [data, isDark]);
}

export function useSetAccountColor(target: AccountColorTarget) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const path =
    "accountId" in target
      ? `/api/account-colors/accounts/${encodeURIComponent(target.accountId)}`
      : `/api/account-colors/model-sources/${encodeURIComponent(target.modelSourceId)}`;
  return useMutation({
    mutationFn: (chartColor: number | null) =>
      put(path, AccountColorsResponseSchema, { body: { chartColor } }),
    onSuccess: async (data) => {
      client.setQueryData(ACCOUNT_COLORS_QUERY_KEY, data);
      await client.invalidateQueries({ queryKey: ["api-keys", "usage-7d"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("accounts.toasts.colorUpdateFailed"));
    },
  });
}
