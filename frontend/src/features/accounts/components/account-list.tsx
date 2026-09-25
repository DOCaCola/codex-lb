import { ChevronDown, ChevronUp, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AccountListItem } from "@/features/accounts/components/account-list-item";
import { AddAccountDialog } from "@/features/accounts/components/add-account-dialog";
import { WindowsOauthHelp } from "@/features/accounts/components/windows-oauth-help";
import type { AccountSummary } from "@/features/accounts/schemas";
import {
  ACCOUNT_SORT_OPTIONS,
  DEFAULT_ACCOUNT_SORT_MODE,
  sortAccountsForDisplay,
  type AccountSortMode,
} from "@/features/accounts/sorting";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { cn } from "@/lib/utils";
import { formatSlug } from "@/utils/formatters";
import type { OpenRouterAccount } from "@/features/openrouter/api";
import { OpenRouterListItem } from "@/features/openrouter/account-display";
import { openRouterStatus } from "@/features/openrouter/display-values";

const STATUS_FILTER_OPTIONS = [
  "all",
  "active",
  "paused",
  "rate_limited",
  "quota_exceeded",
  "reauth_required",
  "deactivated",
];

export type AccountListProps = {
  accounts: AccountSummary[];
  openRouterAccounts?: OpenRouterAccount[];
  onOpenRouter?: () => void;
  selectedAccountId: string | null;
  onSelect: (accountId: string) => void;
  onOpenImport: () => void;
  onOpenOauth: () => void;
  sortMode?: AccountSortMode;
  onSortModeChange?: (sortMode: AccountSortMode) => void;
  showResetCreditBadges?: boolean;
  readOnly?: boolean;
};

export function AccountList({
  accounts,
  openRouterAccounts = [],
  onOpenRouter,
  selectedAccountId,
  onSelect,
  onOpenImport,
  onOpenOauth,
  sortMode,
  onSortModeChange,
  showResetCreditBadges = true,
  readOnly = false,
}: AccountListProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [helpOpen, setHelpOpen] = useState(false);
  const [chooserOpen, setChooserOpen] = useState(false);
  const quotaDisplay = useAccountQuotaDisplayStore((s) => s.quotaDisplay);
  const activeSortMode = sortMode ?? DEFAULT_ACCOUNT_SORT_MODE;

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return sortAccountsForDisplay(
      accounts,
      quotaDisplay,
      activeSortMode,
    ).filter((account) => {
      if (statusFilter !== "all" && account.status !== statusFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        account.email.toLowerCase().includes(needle) ||
        (account.alias?.toLowerCase().includes(needle) ?? false) ||
        account.displayName.toLowerCase().includes(needle) ||
        account.accountId.toLowerCase().includes(needle) ||
        account.planType.toLowerCase().includes(needle)
      );
    });
  }, [accounts, quotaDisplay, search, statusFilter, activeSortMode]);

  const entries = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const providerAccounts = openRouterAccounts
      .filter(
        (account) =>
          (statusFilter === "all" ||
            openRouterStatus(account) === statusFilter) &&
          (!needle ||
            `${account.name} ${account.id} openrouter`
              .toLowerCase()
              .includes(needle)),
      )
      .sort((a, b) => a.name.localeCompare(b.name));
    const result = [
      ...filtered.map((account) => ({
        kind: "codex" as const,
        id: account.accountId,
        name: account.displayName || account.email,
        account,
      })),
      ...providerAccounts.map((account) => ({
        kind: "openrouter" as const,
        id: account.id,
        name: account.name,
        account,
      })),
    ];
    if (activeSortMode === "name_asc" || activeSortMode === "name_desc") {
      result.sort(
        (a, b) =>
          (activeSortMode === "name_desc" ? -1 : 1) *
          a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
      );
    }
    return result;
  }, [filtered, openRouterAccounts, search, statusFilter, activeSortMode]);
  const totalCount = accounts.length + openRouterAccounts.length;

  return (
    <div className="flex max-h-[calc(100dvh-15rem)] min-h-0 min-w-0 flex-1 flex-col space-y-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="relative min-w-0 sm:col-span-2">
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60"
            aria-hidden
          />
          <Input
            placeholder={t("accounts.list.searchPlaceholder")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger
            size="sm"
            className="w-full min-w-0"
            aria-label={t("accounts.list.statusFilterAria")}
          >
            <SelectValue placeholder={t("accounts.list.statusPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {STATUS_FILTER_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {option === "all"
                  ? t("accounts.list.allStatuses")
                  : t(`accounts.statusFilters.${option}`, {
                      defaultValue: formatSlug(option),
                    })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={activeSortMode}
          onValueChange={(nextMode) =>
            onSortModeChange?.(nextMode as AccountSortMode)
          }
        >
          <SelectTrigger
            size="sm"
            className="w-full min-w-0"
            aria-label={t("accounts.list.sortAria")}
          >
            <SelectValue placeholder={t("accounts.list.sortPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {ACCOUNT_SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {t(`accounts.sort.${option.value}`, {
                  defaultValue: option.label,
                })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div
        className={cn(
          "flex flex-wrap items-center gap-3",
          readOnly ? "justify-end" : "justify-between",
        )}
      >
        {readOnly ? null : (
          <Button
            type="button"
            variant="link"
            size="sm"
            className="h-auto px-0 text-xs"
            onClick={() => setHelpOpen((current) => !current)}
          >
            {t("accounts.list.needHelp")}
            {helpOpen ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          className="gap-1.5"
          disabled={readOnly}
          onClick={() => setChooserOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" />
          {t("accounts.list.addAccount")}
        </Button>
      </div>

      {helpOpen && !readOnly ? <WindowsOauthHelp /> : null}

      <div
        className="flex-1 min-h-0 space-y-1 overflow-y-auto p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        data-testid="account-list-scroll-region"
      >
        {entries.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              {totalCount === 0
                ? t("accounts.list.emptyTitle")
                : t("accounts.list.noMatches")}
            </p>
            <p className="text-xs text-muted-foreground/70">
              {totalCount === 0
                ? t("accounts.list.emptyDescription")
                : t("accounts.list.adjustFilters")}
            </p>
          </div>
        ) : (
          entries.map((entry) =>
            entry.kind === "openrouter" ? (
              <OpenRouterListItem
                key={entry.id}
                account={entry.account}
                selected={entry.id === selectedAccountId}
                onSelect={onSelect}
              />
            ) : (
              <AccountListItem
                key={entry.id}
                account={entry.account}
                selected={entry.id === selectedAccountId}
                showAccountId={entry.account.isEmailDuplicate === true}
                showResetCreditBadge={showResetCreditBadges}
                onSelect={onSelect}
              />
            ),
          )
        )}
      </div>

      {accounts.length > 0 ? (
        <p className="px-1 text-[11px] leading-snug text-muted-foreground/80">
          {t("accounts.list.statusEligibilityNote")}
        </p>
      ) : null}

      <AddAccountDialog
        open={chooserOpen}
        onOpenChange={setChooserOpen}
        onImport={onOpenImport}
        onAddAccount={onOpenOauth}
        onOpenRouter={onOpenRouter}
      />
    </div>
  );
}
