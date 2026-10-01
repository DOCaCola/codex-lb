import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePermission } from "@/features/auth/hooks/use-auth";
import { ClaudeCacheActivitySchema } from "@/features/dashboard/schemas";
import { get } from "@/lib/api-client";
import { formatCompactNumber } from "@/utils/formatters";

export function ClaudeCacheActivity({
  accountLabels,
}: {
  accountLabels: Record<string, string>;
}) {
  const { t } = useTranslation();
  const allowed = usePermission("accounts:read");
  const query = useQuery({
    queryKey: ["claude-cache-activity"],
    queryFn: () =>
      get("/api/request-logs/claude-cache-activity", ClaudeCacheActivitySchema),
    enabled: allowed,
    staleTime: 60_000,
    refetchInterval: false,
    retry: false,
  });
  if (!allowed) return null;
  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="text-sm font-semibold">
        {t("reports.claudeCache.title")}
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {t("reports.claudeCache.description")}
      </p>
      {query.error ? (
        <div className="mt-3 space-y-2">
          <AlertMessage variant="error">{query.error.message}</AlertMessage>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void query.refetch()}
          >
            {t("common.actions.retry")}
          </Button>
        </div>
      ) : query.isPending ? (
        <p className="mt-3 text-sm">{t("common.loading")}</p>
      ) : query.data.groups.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          {t("reports.claudeCache.empty")}
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("reports.claudeCache.model")}</TableHead>
                <TableHead>{t("reports.claudeCache.current")}</TableHead>
                <TableHead>{t("reports.claudeCache.previous")}</TableHead>
                <TableHead>{t("reports.claudeCache.writes")}</TableHead>
                <TableHead>{t("reports.claudeCache.measured")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.groups.map((group) => (
                <TableRow key={JSON.stringify([group.sourceId, group.model])}>
                  <TableCell>
                    <span translate="no" className="font-mono text-xs">
                      {group.model}
                    </span>
                    <div className="text-xs text-muted-foreground">
                      {group.sourceId
                        ? (accountLabels[group.sourceId] ??
                          group.sourceId.slice(0, 8))
                        : "—"}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {ratio(group.current.cacheReadRatio)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {ratio(group.previous.cacheReadRatio)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {group.current.measuredRequests
                      ? formatCompactNumber(group.current.cacheWriteTokens)
                      : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {group.current.measuredRequests} / {group.current.requests}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

function ratio(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}
